"""Live trading entry point.

Mirrors ``main.py``: instantiates the *same* :class:`HedgeStrategy` with the
*same* :class:`HedgeStrategyConfig` derived from ``config.py``, then attaches
it to a Nautilus ``TradingNode`` driven by the MT5 data + execution client
factories. Backtest/live parity is the project invariant — any strategy
change in ``strategy/`` is automatically inherited by both paths.
"""
from __future__ import annotations

import warnings

import pandas as pd

warnings.filterwarnings("ignore")
pd.options.mode.chained_assignment = None
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*PeriodArray.*")

from nautilus_trader.config import (
    LoggingConfig,
    LiveDataEngineConfig,
    LiveExecEngineConfig,
    TradingNodeConfig,
)
from nautilus_trader.live.node import TradingNode
from nautilus_trader.model.identifiers import TraderId

from config import (
    ATR_MIN_THRESHOLD,
    BROKER_TIMEZONE,
    ENTRY_DELAY_MINS,
    LEVERAGE,
    LOG_LEVEL,
    MAX_HOLD_HOURS,
    RISK_PERCENT,
    SESSION,
    TICKER,
    VWAP_TF_MINS,
)
from magic.candle_logger import setup_live_logging
from magic.connector import Broker
from magic.helpers.constants import MAGIC, MT5_ACCOUNT, MT5_PASSWORD, MT5_SERVER
from nautilus_mt5.data_client import (
    MT5_VENUE_STR,
    MT5DataClientConfig,
    MT5LiveDataClientFactory,
)
from nautilus_mt5.exec_client import MT5ExecClientConfig, MT5LiveExecClientFactory
from strategy.hedge_strategy import HedgeStrategy, HedgeStrategyConfig
from utils.maps import tz_map
from utils.nautilus_converter import setup_forex_instrument

logger = setup_live_logging()


def _build_strategy():
    """Construct ``HedgeStrategy`` with the identical config the backtest uses."""
    instrument = setup_forex_instrument(TICKER, venue=MT5_VENUE_STR)
    cfg = HedgeStrategyConfig(
        instrument_id=str(instrument.id),
        leverage=LEVERAGE,
        session=SESSION,
        entry_delay_mins=ENTRY_DELAY_MINS,
        vwap_tf_mins=VWAP_TF_MINS,
        risk_percent=RISK_PERCENT,
        atr_min_threshold=ATR_MIN_THRESHOLD.get(TICKER, 0.0),
        max_hold_hours=MAX_HOLD_HOURS,
    )
    return HedgeStrategy(config=cfg), instrument


def main() -> None:
    # ── Pre-flight: log in to MT5 with our broker wrapper. The clients each
    # call mt5.initialize() too — MT5's Python API is process-singleton, so
    # the second call is a no-op as long as the credentials match.
    broker = Broker(magic_no=MAGIC)
    broker.login(username=MT5_ACCOUNT, password=MT5_PASSWORD, server=MT5_SERVER)
    broker.configure(debug=False, tz=tz_map[BROKER_TIMEZONE])
    broker.connect()
    account = broker.get_account()
    logger.info(
        f"Connected to MT5 | Balance: {account['balance']} | Server: {MT5_SERVER}"
    )

    # ── TradingNode wiring ──────────────────────────────────────────────
    node_cfg = TradingNodeConfig(
        trader_id=TraderId("LIVE-001"),
        logging=LoggingConfig(log_level=LOG_LEVEL),
        data_engine=LiveDataEngineConfig(),
        exec_engine=LiveExecEngineConfig(reconciliation=False),
        data_clients={MT5_VENUE_STR: MT5DataClientConfig()},
        exec_clients={MT5_VENUE_STR: MT5ExecClientConfig()},
    )
    node = TradingNode(config=node_cfg)
    node.add_data_client_factory(MT5_VENUE_STR, MT5LiveDataClientFactory)
    node.add_exec_client_factory(MT5_VENUE_STR, MT5LiveExecClientFactory)
    node.build()

    # Add the instrument to the kernel cache so the strategy can resolve it
    # immediately on start (clients also re-add via their providers).
    strategy, instrument = _build_strategy()
    node.kernel.cache.add_instrument(instrument)
    node.trader.add_strategy(strategy)
    logger.info(
        f"[strategy] {type(strategy).__name__} on {instrument.id} "
        f"session={SESSION} risk_percent={RISK_PERCENT} "
        f"atr_min={ATR_MIN_THRESHOLD.get(TICKER, 0.0)} max_hold={MAX_HOLD_HOURS}h"
    )

    logger.info("Initializing Native Nautilus Live Trading Engine...")
    try:
        node.run()
    except KeyboardInterrupt:
        logger.info("Shutdown requested.")
    finally:
        node.dispose()
        logger.info("Live Node offline.")


if __name__ == "__main__":
    main()
