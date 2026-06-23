"""
MT5 redundancy source for the data-fetching pipeline.

Used when a ticker is not available on Polygon. Fetches 1-minute OHLCV
candles directly from MetaTrader 5 and returns a DataFrame with the exact
same schema as `storelib.urls.get_ticker` (UTC-indexed OHLCV) so the rest
of the storage pipeline is unchanged.

MT5 only returns ~60 days of 1M data per `copy_rates_range` call, so the
requested window is split into 60-day chunks and stitched back together.
"""

import logging
from datetime import datetime, timedelta

import pandas as pd
import pytz

from config import BROKER_TIMEZONE
from utils.maps import tz_map
from magic.connector import Broker
from magic.helpers.utils import get_candles_df
from magic.helpers.constants import (
    MT5_ACCOUNT,
    MT5_PASSWORD,
    MT5_SERVER,
    MT5_PATH,
    MAGIC,
    map_symbol,
)

logger = logging.getLogger("backtest")

# MT5 hard limit: a single copy_rates_range call returns at most ~60 days
# of 1-minute bars. Stay just under it to be safe.
CHUNK_DAYS = 60


_broker: Broker | None = None


def _get_broker() -> Broker:
    """Lazily create and connect a single shared MT5 Broker."""
    global _broker
    if _broker is not None and _broker.tickers.check_connection():
        return _broker

    broker = Broker(magic_no=MAGIC)
    broker.login(
        username=MT5_ACCOUNT,
        password=MT5_PASSWORD,
        server=MT5_SERVER,
        path=MT5_PATH or None,
    )
    broker.configure(debug=False, tz=tz_map[BROKER_TIMEZONE])
    broker.connect()

    if not broker.connected:
        raise ConnectionError(
            f"Could not connect to MT5 ({MT5_SERVER}) for redundancy fetch"
        )

    _broker = broker
    return _broker


def _to_utc_datetime(value) -> datetime:
    """Accept pendulum / datetime / str and return a tz-aware UTC datetime.

    Uses pandas to parse so pendulum.DateTime, naive/aware datetimes and
    ISO strings all normalize consistently to a stdlib UTC datetime.
    """
    ts = pd.Timestamp(str(value))
    ts = ts.tz_localize("UTC") if ts.tz is None else ts.tz_convert("UTC")
    return ts.to_pydatetime()


def _mt5_symbol(symbol: str) -> str:
    """Map a Polygon ticker (e.g. 'C:XAUUSD' / 'X:BTCUSD') to an MT5 symbol."""
    base = symbol.split(":", 1)[1] if ":" in symbol else symbol
    return map_symbol(base)


def fetch_mt5(symbol: str, start, end) -> pd.DataFrame:
    """Fetch 1M OHLCV candles from MT5 for `symbol` between `start` and `end`.

    Returns a DataFrame matching the Polygon schema: a UTC-tz-aware
    `Datetime` index with `Open, High, Low, Close, Volume` columns.
    """
    broker = _get_broker()
    mt5_symbol = _mt5_symbol(symbol)

    select = broker.tickers.select(mt5_symbol)
    if select.get("is_error") or not select.get("data"):
        raise ValueError(f"Symbol '{mt5_symbol}' not available on MT5")

    start_dt = _to_utc_datetime(start)
    end_dt = _to_utc_datetime(end)

    frames: list[pd.DataFrame] = []
    chunk_start = start_dt

    while chunk_start < end_dt:
        chunk_end = min(chunk_start + timedelta(days=CHUNK_DAYS), end_dt)

        logger.info(
            f"[MT5] Fetching {mt5_symbol} 1M {chunk_start.date()} -> {chunk_end.date()}"
        )

        result = broker.tickers.candles(
            mt5_symbol, "1M", from_dt=chunk_start, to_dt=chunk_end
        )

        if result["is_error"] or result["data"] is None or len(result["data"]) == 0:
            logger.warning(
                f"[MT5] No data for {mt5_symbol} "
                f"{chunk_start.date()} -> {chunk_end.date()} "
                f"({result.get('error')})"
            )
        else:
            frames.append(get_candles_df(result["data"], pytz.utc))

        chunk_start = chunk_end

    if not frames:
        raise ValueError(
            f"MT5 returned no data for '{mt5_symbol}' "
            f"between {start_dt.date()} and {end_dt.date()}"
        )

    df = pd.concat(frames).sort_index()
    df = df[~df.index.duplicated(keep="first")]
    df = df.rename(
        columns={
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "tick_volume": "Volume",
        }
    )
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.index.name = "Datetime"

    logger.info(f"[MT5] Fetched {len(df)} 1M bars for {mt5_symbol}")
    return df
