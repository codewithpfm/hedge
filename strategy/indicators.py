from datetime import datetime, timezone

from nautilus_trader.indicators.averages import (
    ExponentialMovingAverage,
    MovingAverageType,
    WilderMovingAverage,
)
from nautilus_trader.indicators.momentum import RelativeStrengthIndex
from nautilus_trader.indicators.trend import (
    DirectionalMovement,
    MovingAverageConvergenceDivergence,
)
from nautilus_trader.indicators.volatility import AverageTrueRange
from nautilus_trader.model.data import Bar

from config import SESSION
from utils.maps import session_bucket


def _bar_date(bar: Bar):
    """UTC calendar date of a bar from its event timestamp (ns)."""
    return datetime.fromtimestamp(bar.ts_event / 1e9, tz=timezone.utc).date()


# --- 3.1 VWAP (30M) -------------------------------------------------------

class SessionVWAP:
    """Rolling VWAP from session start, with previous-session carry-over.

    The VWAP is accumulated directly (typical price * volume) and reset on
    each new trading session as defined by ``config.SESSION`` — e.g.
    ``"london"`` anchors the reset to the London open (07:00 UTC) rather
    than UTC midnight. The last value of the prior session is snapshotted
    just before the reset so it remains available as ``previous_session``
    (and via ``effective`` before the new session prints its first bar).

    Feed this 30-minute bars.
    """

    def __init__(self, session: str | None = None) -> None:
        self._session_name = session if session is not None else SESSION
        self._bucket = None
        self._cum_pv = 0.0
        self._cum_vol = 0.0
        self._value = 0.0
        self._initialized = False
        self.previous_session: float | None = None

    def handle_bar(self, bar: Bar) -> None:
        ts = datetime.fromtimestamp(bar.ts_event / 1e9, tz=timezone.utc)
        bucket = session_bucket(ts, self._session_name)
        if self._bucket is not None and bucket != self._bucket and self._initialized:
            self.previous_session = self._value
            self._cum_pv = 0.0
            self._cum_vol = 0.0
            self._initialized = False
        self._bucket = bucket

        typical = (float(bar.high) + float(bar.low) + float(bar.close)) / 3.0
        vol = float(bar.volume)
        self._cum_pv += typical * vol
        self._cum_vol += vol
        if self._cum_vol > 0.0:
            self._value = self._cum_pv / self._cum_vol
            self._initialized = True

    @property
    def value(self) -> float:
        """Current session VWAP (from session start)."""
        return self._value

    @property
    def effective(self) -> float | None:
        """Session VWAP if the session has data, else the carry-over value."""
        if self._initialized:
            return self._value
        return self.previous_session

    @property
    def initialized(self) -> bool:
        return self._initialized

    def reset(self) -> None:
        self._bucket = None
        self._cum_pv = 0.0
        self._cum_vol = 0.0
        self._value = 0.0
        self._initialized = False
        self.previous_session = None


# --- 3.4 ADX (14) ---------------------------------------------------------

class ADX:
    """Average Directional Index.

    Nautilus ships ``DirectionalMovement`` (+DI / -DI) but not ADX, so DX is
    derived from the DI pair and Wilder-smoothed with Nautilus
    ``WilderMovingAverage``. ``active`` implements the "ADX > 20" gate.
    """

    def __init__(self, period: int = 14, threshold: float = 20.0) -> None:
        self.period = period
        self.threshold = threshold
        self._dm = DirectionalMovement(period)
        self._adx = WilderMovingAverage(period)
        self.value: float = 0.0

    def handle_bar(self, bar: Bar) -> None:
        self._dm.handle_bar(bar)
        pos, neg = self._dm.pos, self._dm.neg
        denom = pos + neg
        dx = 100.0 * abs(pos - neg) / denom if denom > 0 else 0.0
        self._adx.update_raw(dx)
        self.value = self._adx.value

    @property
    def pos(self) -> float:
        """+DI."""
        return self._dm.pos

    @property
    def neg(self) -> float:
        """-DI."""
        return self._dm.neg

    @property
    def initialized(self) -> bool:
        return self._dm.initialized and self._adx.initialized

    @property
    def active(self) -> bool:
        """True only when trend strength clears the threshold (ADX > 20)."""
        return self.initialized and self.value > self.threshold

    def reset(self) -> None:
        self._dm.reset()
        self._adx.reset()
        self.value = 0.0


# --- 3.6 MACD (12, 26, 9) -------------------------------------------------

class MACD:
    """MACD line + signal + histogram.

    Nautilus ``MovingAverageConvergenceDivergence`` only emits the MACD line;
    the signal line is a Nautilus EMA of that line and the histogram is their
    difference.
    """

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9) -> None:
        self._macd = MovingAverageConvergenceDivergence(
            fast, slow, ma_type=MovingAverageType.EXPONENTIAL
        )
        self._signal = ExponentialMovingAverage(signal)
        self.value: float = 0.0
        self.signal: float = 0.0
        self.histogram: float = 0.0

    def handle_bar(self, bar: Bar) -> None:
        self._macd.handle_bar(bar)
        self.value = self._macd.value
        self._signal.update_raw(self.value)
        self.signal = self._signal.value
        self.histogram = self.value - self.signal

    @property
    def bullish(self) -> bool:
        return self.initialized and self.histogram > 0.0

    @property
    def initialized(self) -> bool:
        return self._macd.initialized and self._signal.initialized

    def reset(self) -> None:
        self._macd.reset()
        self._signal.reset()
        self.value = self.signal = self.histogram = 0.0


# --- 3.2 / 3.3 / 3.5 / 3.7 + composite (all on 1D) ------------------------

class DailyIndicators:
    """Previous-day daily indicator set.

    Feed completed daily bars via :meth:`handle_bar`. A bar is ingested only
    when its date advances past the last ingested one, so repeatedly feeding
    an in-progress daily bar will not corrupt the "previous day" values.

      * 3.2 ATR(14)  - Wilder
      * 3.3 EMA(50)
      * 3.4 ADX(14)  - with > threshold gate
      * 3.5 RSI(14)  - Wilder
      * 3.6 MACD(12, 26, 9)
      * 3.7 Previous Day High / Low (and Close)
    """

    def __init__(
        self,
        atr_period: int = 14,
        ema_period: int = 50,
        adx_period: int = 14,
        adx_threshold: float = 20.0,
        rsi_period: int = 14,
        macd_periods: tuple[int, int, int] = (12, 26, 9),
    ) -> None:
        self.atr = AverageTrueRange(atr_period, ma_type=MovingAverageType.WILDER)
        self.ema = ExponentialMovingAverage(ema_period)
        self.adx = ADX(adx_period, adx_threshold)
        self.rsi = RelativeStrengthIndex(rsi_period, ma_type=MovingAverageType.WILDER)
        self.macd = MACD(*macd_periods)

        self.prev_high: float | None = None
        self.prev_low: float | None = None
        self.prev_close: float | None = None
        self._last_date = None

    def handle_bar(self, bar: Bar) -> None:
        day = _bar_date(bar)
        if self._last_date is not None and day <= self._last_date:
            return  # only ingest newly completed (advancing) daily bars
        self._last_date = day

        self.atr.handle_bar(bar)
        self.ema.handle_bar(bar)
        self.adx.handle_bar(bar)
        self.rsi.handle_bar(bar)
        self.macd.handle_bar(bar)

        self.prev_high = float(bar.high)
        self.prev_low = float(bar.low)
        self.prev_close = float(bar.close)

    @property
    def initialized(self) -> bool:
        return all(
            ind.initialized
            for ind in (self.atr, self.ema, self.adx, self.rsi, self.macd)
        ) and self.prev_high is not None

    def snapshot(self) -> dict:
        """Flat dict of current previous-day values (handy for logging)."""
        return {
            "atr": self.atr.value,
            "ema50": self.ema.value,
            "adx": self.adx.value,
            "adx_active": self.adx.active,
            "di_pos": self.adx.pos,
            "di_neg": self.adx.neg,
            "rsi": self.rsi.value,
            "macd": self.macd.value,
            "macd_signal": self.macd.signal,
            "macd_hist": self.macd.histogram,
            "prev_high": self.prev_high,
            "prev_low": self.prev_low,
            "prev_close": self.prev_close,
        }

    def reset(self) -> None:
        self.atr.reset()
        self.ema.reset()
        self.adx.reset()
        self.rsi.reset()
        self.macd.reset()
        self.prev_high = self.prev_low = self.prev_close = None
        self._last_date = None


# Backwards-compatible alias (previous module exposed ``VWAP``).
VWAP = SessionVWAP
