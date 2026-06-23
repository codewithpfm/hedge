"""MT5 live data client (+ instrument provider, config, factory).

Polls MetaTrader 5 for completed 1-minute bars and feeds them into the
Nautilus data engine as ``Bar`` events. This is the live counterpart of the
parquet-fed ``BarDataWrangler`` path in ``main.py`` — the strategy
(``HedgeStrategy``) subscribes to ``<INSTRUMENT>-1-MINUTE-LAST-EXTERNAL``
bars and is agnostic to whether they came from disk or MT5.

The ``MT5InstrumentProvider`` lives in this module because it owns
instrument-metadata loading (a data concern); the exec client imports it
from here. The factory + config sit alongside the client they construct so
``TradingNode`` can wire everything via ``add_data_client_factory``.
"""
from __future__ import annotations

import asyncio

import MetaTrader5 as mt5  # type: ignore
import pandas as pd
from nautilus_trader.cache.cache import Cache
from nautilus_trader.common.component import LiveClock, MessageBus
from nautilus_trader.common.providers import InstrumentProvider
from nautilus_trader.config import LiveDataClientConfig
from nautilus_trader.core.datetime import dt_to_unix_nanos
from nautilus_trader.live.data_client import LiveDataClient
from nautilus_trader.live.factories import LiveDataClientFactory
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.identifiers import ClientId, InstrumentId, Venue
from nautilus_trader.model.instruments import Instrument
from nautilus_trader.model.objects import Price, Quantity

from config import TICKER
from magic.helpers.constants import MAGIC
from utils.nautilus_converter import setup_forex_instrument

MT5_VENUE_STR = "MT5"


# ─────────────────────────────────────────────────────────────────────────
# Instrument provider — shared by the exec client (imported from here)
# ─────────────────────────────────────────────────────────────────────────
class MT5InstrumentProvider(InstrumentProvider):
    """Single-symbol provider for the currently configured live ticker.

    Pre-loads the configured ``TICKER`` (via :func:`setup_forex_instrument`)
    on ``initialize`` so both the data and exec clients can look it up.
    """

    def __init__(self, venue: str = MT5_VENUE_STR) -> None:
        super().__init__()
        self._venue = venue

    async def load_all_async(self, filters: dict | None = None) -> None:
        instrument = setup_forex_instrument(TICKER, venue=self._venue)
        self.add(instrument)
        self.add_currency(instrument.base_currency)
        self.add_currency(instrument.quote_currency)
        self._loaded = True

    async def load_ids_async(
        self,
        instrument_ids: list[InstrumentId],
        filters: dict | None = None,
    ) -> None:
        if not self._loaded:
            await self.load_all_async(filters)

    def find_by_symbol(self, symbol: str) -> Instrument | None:
        for inst in self.list_all():
            if inst.id.symbol.value == symbol:
                return inst
        return None


# ─────────────────────────────────────────────────────────────────────────
# Data client
# ─────────────────────────────────────────────────────────────────────────
class MT5DataClient(LiveDataClient):
    """Subclasses Nautilus :class:`LiveDataClient` to feed live MT5 1M bars.

    Bars are pulled with ``mt5.copy_rates_from_pos`` once every ``POLL_SECONDS``;
    the most recent (in-progress) candle is skipped so only closed bars reach
    the strategy — matching the backtest's "bar-on-close" event model.
    """

    POLL_SECONDS = 5.0

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        client_id: ClientId,
        venue: Venue,
        msgbus: MessageBus,
        cache: Cache,
        clock: LiveClock,
        instrument_provider: MT5InstrumentProvider,
        broker_magic: int = MAGIC,
    ) -> None:
        super().__init__(
            loop=loop,
            client_id=client_id,
            venue=venue,
            msgbus=msgbus,
            cache=cache,
            clock=clock,
        )
        self.magic = broker_magic
        self._instrument_provider = instrument_provider
        self._bar_subscriptions: dict[BarType, int] = {}  # bar_type -> last ts_ns
        self._polling_task: asyncio.Task | None = None

    # ── Lifecycle ────────────────────────────────────────────────────────
    async def _connect(self) -> None:
        if not mt5.initialize():
            self._log.error("MT5 initialize failed in DataClient")
            return
        await self._instrument_provider.initialize()
        for inst in self._instrument_provider.list_all():
            self._cache.add_instrument(inst)
        self._log.info("MT5DataClient connected.")
        self._polling_task = self._loop.create_task(self._poll_bars())

    async def _disconnect(self) -> None:
        if self._polling_task:
            self._polling_task.cancel()
        mt5.shutdown()
        self._log.info("MT5DataClient disconnected.")

    # ── Subscription API ─────────────────────────────────────────────────
    async def _subscribe_bars(self, command) -> None:
        bar_type = command.bar_type
        if bar_type not in self._bar_subscriptions:
            self._bar_subscriptions[bar_type] = 0
            self._log.info(f"Subscribed to MT5 bars for {bar_type}")

    async def _unsubscribe_bars(self, command) -> None:
        bar_type = command.bar_type
        self._bar_subscriptions.pop(bar_type, None)
        self._log.info(f"Unsubscribed from MT5 bars for {bar_type}")

    # ── Polling loop ─────────────────────────────────────────────────────
    async def _poll_bars(self) -> None:
        """Pull the latest closed 1M bar for each subscription and dispatch.

        We always read position 1 (skip 0 = currently-forming candle) so the
        strategy only sees finalised bars. Duplicate sends are guarded by
        ``last_ts_ns`` per bar_type.
        """
        while True:
            for bar_type, last_ts_ns in list(self._bar_subscriptions.items()):
                symbol = bar_type.instrument_id.symbol.value
                instrument = self._cache.instrument(bar_type.instrument_id)
                if instrument is None:
                    continue

                rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 1, 1)
                if rates is None or len(rates) == 0:
                    continue

                row = rates[0]
                ts_ns = dt_to_unix_nanos(
                    pd.Timestamp(int(row["time"]), unit="s", tz="UTC")
                )
                if ts_ns <= last_ts_ns:
                    continue

                bar = Bar(
                    bar_type=bar_type,
                    open=Price(float(row["open"]), instrument.price_precision),
                    high=Price(float(row["high"]), instrument.price_precision),
                    low=Price(float(row["low"]), instrument.price_precision),
                    close=Price(float(row["close"]), instrument.price_precision),
                    volume=Quantity(int(row["tick_volume"]), instrument.size_precision),
                    ts_event=ts_ns,
                    ts_init=ts_ns,
                )
                self._handle_data(bar)
                self._bar_subscriptions[bar_type] = ts_ns

            await asyncio.sleep(self.POLL_SECONDS)


# ─────────────────────────────────────────────────────────────────────────
# Config + factory (TradingNode wires the client via these)
# ─────────────────────────────────────────────────────────────────────────
class MT5DataClientConfig(LiveDataClientConfig, frozen=True):
    broker_magic: int = MAGIC


class MT5LiveDataClientFactory(LiveDataClientFactory):
    @staticmethod
    def create(  # type: ignore[override]
        loop: asyncio.AbstractEventLoop,
        name: str,
        config: MT5DataClientConfig,
        msgbus: MessageBus,
        cache: Cache,
        clock: LiveClock,
    ) -> MT5DataClient:
        venue = Venue(MT5_VENUE_STR)
        provider = MT5InstrumentProvider(venue=MT5_VENUE_STR)
        return MT5DataClient(
            loop=loop,
            client_id=ClientId(name),
            venue=venue,
            msgbus=msgbus,
            cache=cache,
            clock=clock,
            instrument_provider=provider,
            broker_magic=config.broker_magic,
        )
