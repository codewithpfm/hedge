import logging
import pandas as pd

from config import SIGNAL_TF, SECONDARY_TIMEFRAME, EMA, VWMA
from blocks.enums import TF_TO_MINUTES, TF_TO_HOURS
from utils.resampler import Resample
from blocks.indicators import Indicators
from blocks.trainer import Trainer
from signals import Signals
from magic.helpers.utils import get_candles_df
from magic.helpers.constants import MT5_SYMBOL, LOOKBACK_DAYS, TRAINING_MONTHS

# Parse SIGNAL_TF (e.g. "8M" → 8, "5M" → 5)
_SIGNAL_MINUTES = int(SIGNAL_TF.replace("M", ""))
_HTF_MINUTES = TF_TO_MINUTES(SECONDARY_TIMEFRAME)
_HTF_HOURS = TF_TO_HOURS(SECONDARY_TIMEFRAME)

# Cached signal bars fed before the new bar so EMA/VWMA warm up.
# EMA_20 needs ~40 bars; VWMA_20 needs exactly 20.
_IND_WARMUP = 40

logger = logging.getLogger("live_engine")


def fetch_candles(broker, days_back=LOOKBACK_DAYS) -> pd.DataFrame:
    """Fetch 1M candles from MT5 using count-based approach.
    Uses copy_rates_from_pos which reliably returns the latest N bars
    in the broker's server timezone, avoiding from_dt/to_dt timezone issues.
    """
    # ~1440 bars/day × days_back, capped at MT5's limit per call
    CHUNK_SIZE = 5000
    total_bars = days_back * 1440
    all_dfs = []

    start_pos = 1  # skip the current (incomplete) bar
    remaining = total_bars

    while remaining > 0:
        count = min(remaining, CHUNK_SIZE)

        result = broker.tickers.candles(MT5_SYMBOL, "1M", start_pos=start_pos, count=count)

        if result["is_error"] or result["data"] is None:
            logger.error(f"Failed to fetch candles chunk: {result.get('error')}")
            break

        df = get_candles_df(result["data"], broker.tz)
        all_dfs.append(df)

        fetched = len(result["data"])
        if fetched < count:
            break  # no more data available

        start_pos += fetched
        remaining -= fetched

    if not all_dfs:
        return pd.DataFrame()

    df = pd.concat(all_dfs).sort_index()
    df = df[~df.index.duplicated(keep='first')]
    df = df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "tick_volume": "Volume"})
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.index.name = "Datetime"
    return df


class SignalComputer:
    def __init__(self):
        self.long_threshold = None
        self.short_threshold = None
        self.long_sl = None
        self.long_tp = None
        self.short_sl = None
        self.short_tp = None
        self._cached_current_month = None
        self._cached_signal_df = None   # Signal TF bars with indicators (full history)
        self._cached_check_df = None    # HTF bars: OHLCV + EMA (SECONDARY_TIMEFRAME)

    # ------------------------------------------------------------------
    #  train() — resample → indicators → Trainer → cache both timeframes
    # ------------------------------------------------------------------
    def train(self, data_1m: pd.DataFrame) -> bool:
        """Resample 1M → {SIGNAL_TF} + {SECONDARY_TIMEFRAME}, train thresholds + SL/TP, cache both.

        Called once at startup and again when the month rolls over.
        - {SIGNAL_TF} with EMA/VWMA: cached for incremental indicator updates.
        - {SECONDARY_TIMEFRAME} with EMA only: cached for HTF exit filter.
        """
        if data_1m.empty or len(data_1m) < 100:
            logger.warning("Insufficient data for training")
            return False

        resampled = Resample(data_1m)
        signal_data = resampled.get(SIGNAL_TF)
        check_data = resampled.get(SECONDARY_TIMEFRAME)

        if signal_data.empty or check_data.empty:
            logger.warning("Resampled data is empty")
            return False

        # Signal TF: full indicators — cached for incremental use by evaluate_bar()
        signal_ind = Indicators(
            signal_data, {"EMA": list(EMA), "VWMA": list(VWMA)}
        ).df.copy()

        # Drop the last bar if it's partial (< _SIGNAL_MINUTES 1M candles).
        # A partial tail bar would cause evaluate_bar() to skip ahead and
        # never build the real complete version.
        if not signal_ind.empty and not data_1m.empty:
            last_bar_ts = signal_ind.index[-1]
            last_bar_end = last_bar_ts + pd.Timedelta(minutes=_SIGNAL_MINUTES - 1)
            n_candles = len(data_1m[
                (data_1m.index >= last_bar_ts) & (data_1m.index <= last_bar_end)
            ])
            if n_candles < _SIGNAL_MINUTES:
                signal_ind = signal_ind.iloc[:-1]
                logger.debug(
                    f"[TRAIN] Dropped partial last {SIGNAL_TF} bar at {last_bar_ts} "
                    f"({n_candles}/{_SIGNAL_MINUTES} candles)"
                )
        self._cached_signal_df = signal_ind

        # HTF: OHLCV + EMA (used for HTF exit filter + incremental updates)
        check_ind = Indicators(check_data, {"EMA": [EMA[-1]]}).df.copy()

        # Drop the last HTF bar if it's partial (< _HTF_MINUTES 1M candles).
        if not check_ind.empty and not data_1m.empty:
            last_htf_ts = check_ind.index[-1]
            last_htf_end = last_htf_ts + pd.Timedelta(hours=_HTF_HOURS, minutes=-1)
            n_candles = len(data_1m[
                (data_1m.index >= last_htf_ts) & (data_1m.index <= last_htf_end)
            ])
            if n_candles < _HTF_MINUTES:
                check_ind = check_ind.iloc[:-1]
                logger.debug(
                    f"[TRAIN] Dropped partial last {SECONDARY_TIMEFRAME} bar at {last_htf_ts} "
                    f"({n_candles}/{_HTF_MINUTES} candles)"
                )
        self._cached_check_df = check_ind

        unique_months = self._cached_signal_df.index.to_period("M").unique()
        if len(unique_months) < TRAINING_MONTHS + 1:
            logger.warning(f"Only {len(unique_months)} months, need {TRAINING_MONTHS + 1}")
            return False

        current_month = unique_months[-1]
        train_months = unique_months[-(TRAINING_MONTHS + 1):-1]
        t_signal_data = self._cached_signal_df[
            self._cached_signal_df.index.to_period("M").isin(train_months)
        ]

        trainer = Trainer(t_signal_data)
        self.long_threshold = trainer.calc_threshold(f"EMA_{EMA[0]}", f"VWMA_{VWMA[0]}", "long")
        self.short_threshold = trainer.calc_threshold(f"EMA_{EMA[0]}", f"VWMA_{VWMA[0]}", "short")
        self.long_sl, self.long_tp = trainer.calc_sltp_pct(f"EMA_{EMA[0]}", f"VWMA_{VWMA[0]}", "long")
        self.short_sl, self.short_tp = trainer.calc_sltp_pct(f"EMA_{EMA[0]}", f"VWMA_{VWMA[0]}", "short")
        self._cached_current_month = current_month

        logger.info(
            f"Trained for {current_month} on months {list(train_months)} | "
            f"L_thresh: {self.long_threshold:.6f} | S_thresh: {self.short_threshold:.6f} | "
            f"L_SL: {self.long_sl:.6f} | L_TP: {self.long_tp:.6f} | "
            f"S_SL: {self.short_sl:.6f} | S_TP: {self.short_tp:.6f} | "
            f"{SIGNAL_TF} cache: {len(self._cached_signal_df)} bars | "
            f"{SECONDARY_TIMEFRAME} cache: {len(self._cached_check_df)} bars"
        )
        return True

    # ------------------------------------------------------------------
    #  update_check_df() — build new HTF bars via Indicators (exact ewm match)
    # ------------------------------------------------------------------
    def update_check_df(self, data_1m: pd.DataFrame) -> None:
        """Append any new complete HTF bars to _cached_check_df.

        Uses Indicators on 40-bar cache tail + new bar so EMA is
        computed with the same ewm() logic as train(). No manual alpha.
        """
        if self._cached_check_df is None or data_1m.empty:
            return

        ema_col = f"EMA_{EMA[-1]}"

        while True:
            cache_end = self._cached_check_df.index[-1]
            next_start = cache_end + pd.Timedelta(hours=_HTF_HOURS)

            # Is this HTF bar complete? Data must exist past its end.
            if data_1m.index[-1] < next_start + pd.Timedelta(hours=_HTF_HOURS):
                break

            next_end = next_start + pd.Timedelta(hours=_HTF_HOURS, minutes=-1)
            candles = data_1m[
                (data_1m.index >= next_start) & (data_1m.index <= next_end)
            ]
            if candles.empty:
                # Gap (weekend/holiday): jump ahead to next HTF slot with data
                future = data_1m[data_1m.index > next_end]
                if future.empty:
                    break
                first_after = future.index[0]
                aligned_hour = (first_after.hour // _HTF_HOURS) * _HTF_HOURS
                next_start = first_after.replace(
                    hour=aligned_hour, minute=0, second=0, microsecond=0
                )
                next_end = next_start + pd.Timedelta(hours=_HTF_HOURS, minutes=-1)
                candles = data_1m[
                    (data_1m.index >= next_start) & (data_1m.index <= next_end)
                ]
                if candles.empty or data_1m.index[-1] < next_start + pd.Timedelta(hours=_HTF_HOURS):
                    break
                logger.info(
                    f"[{SECONDARY_TIMEFRAME} GAP SKIP] {cache_end} -> {next_start}"
                )

            # Build one HTF bar from 1M candles
            new_bar = pd.DataFrame({
                "Open": [candles["Open"].iloc[0]],
                "High": [candles["High"].max()],
                "Low": [candles["Low"].min()],
                "Close": [candles["Close"].iloc[-1]],
                "Volume": [candles["Volume"].sum()],
            }, index=pd.DatetimeIndex([next_start], name="Datetime"))

            # 40-bar tail (OHLCV) + new bar → Indicators → take last row
            tail_ohlcv = self._cached_check_df[["Open", "High", "Low", "Close", "Volume"]].iloc[-_IND_WARMUP:]
            slice_raw = pd.concat([tail_ohlcv, new_bar])
            slice_with_ind = Indicators(slice_raw, {"EMA": [EMA[-1]]}).df

            self._cached_check_df = pd.concat([self._cached_check_df, slice_with_ind.iloc[[-1]]])

            latest = self._cached_check_df.iloc[-1]
            logger.debug(
                f"[{SECONDARY_TIMEFRAME} UPDATE] {next_start} | Close: {latest['Close']:.5f} | "
                f"EMA_{EMA[-1]}: {latest[ema_col]:.5f} | Cache: {len(self._cached_check_df)} bars"
            )

    # ------------------------------------------------------------------
    #  evaluate_bar() — build new signal bar from 1M, indicators, signals
    # ------------------------------------------------------------------
    def evaluate_bar(self, data_1m: pd.DataFrame) -> dict | None:
        """Build new {SIGNAL_TF} bar from 1M candles, compute indicators
        on cache tail + new bar, run Signals for entry/exit.

        Called by signal_job at {SIGNAL_TF} boundaries.
        """
        if data_1m.empty or self._cached_signal_df is None:
            return None

        current_month = data_1m.index[-1].to_period("M")

        # Train if needed (first run or month rolled)
        if (self._cached_current_month is None
                or self.long_threshold is None
                or current_month != self._cached_current_month):
            if not self.train(data_1m):
                return None

        # --- Step 1: find 1M candles for the next signal bar ---
        cache_end_ts = self._cached_signal_df.index[-1]

        # Skip market-close gaps: if the 1M cache has data well past the
        # next bar window but fewer than _SIGNAL_MINUTES candles exist,
        # the bar falls in a gap (daily close, weekend, holiday).
        _max_skip = 2000         # ~7 days of 5M bars (covers weekends + holidays)
        _skipped = 0
        while _skipped < _max_skip:
            next_bar_start = cache_end_ts + pd.Timedelta(minutes=_SIGNAL_MINUTES)
            next_bar_end = next_bar_start + pd.Timedelta(minutes=_SIGNAL_MINUTES - 1)

            candles_for_bar = data_1m[
                (data_1m.index >= next_bar_start) & (data_1m.index <= next_bar_end)
            ]

            if len(candles_for_bar) >= _SIGNAL_MINUTES:
                break  # found a buildable bar

            # 1M data exists past this bar's window → bar is in a gap, skip it
            if not data_1m.empty and data_1m.index[-1] > next_bar_end:
                cache_end_ts = next_bar_start  # advance pointer
                _skipped += 1
                continue

            # No data past this window yet → bar simply hasn't closed
            return None

        if _skipped:
            logger.info(
                f"[GAP SKIP] Skipped {_skipped} empty {SIGNAL_TF} slots "
                f"({self._cached_signal_df.index[-1]} -> {next_bar_start})"
            )
        if len(candles_for_bar) < _SIGNAL_MINUTES:
            return None

        # --- Step 3: build one signal bar ---
        new_bar = pd.DataFrame({
            "Open": [candles_for_bar["Open"].iloc[0]],
            "High": [candles_for_bar["High"].max()],
            "Low": [candles_for_bar["Low"].min()],
            "Close": [candles_for_bar["Close"].iloc[-1]],
            "Volume": [candles_for_bar["Volume"].sum()],
        }, index=pd.DatetimeIndex([next_bar_start], name="Datetime"))

        # --- Step 4: tail from cache + new bar → compute indicators ---
        tail_ohlcv = self._cached_signal_df[
            ["Open", "High", "Low", "Close", "Volume"]
        ].iloc[-_IND_WARMUP:]

        slice_raw = pd.concat([tail_ohlcv, new_bar])
        slice_with_ind = Indicators(
            slice_raw, {"EMA": list(EMA), "VWMA": list(VWMA)}
        ).df

        # --- Step 5: append new bar (with indicators) to cache ---
        new_with_ind = slice_with_ind.iloc[[-1]]
        self._cached_signal_df = pd.concat([self._cached_signal_df, new_with_ind])

        logger.debug(
            f"[NEW {SIGNAL_TF} BAR] {next_bar_start} | Close: {new_bar['Close'].iloc[0]:.5f} | "
            f"Cache: {len(self._cached_signal_df)} bars"
        )

        # --- Step 6: exit detection on completed bar N (Signals class) ---
        signal_window = slice_with_ind.iloc[-5:]
        if len(signal_window) < 2:
            return None

        check_with_ind = self._cached_check_df
        if check_with_ind is None or check_with_ind.empty:
            return None

        signals = Signals(signal_window, check_with_ind)
        sig_long_entries = signals.get_long_entries(self.long_threshold)
        long_exits, _ = signals.get_long_exits(
            entries=sig_long_entries, sl_pct=self.long_sl, tp_pct=self.long_tp,
        )
        sig_short_entries = signals.get_short_entries(self.short_threshold)
        short_exits, _ = signals.get_short_exits(
            entries=sig_short_entries, sl_pct=self.short_sl, tp_pct=self.short_tp,
        )

        # Exit reason from Signals
        long_exit_reason = ""
        short_exit_reason = ""
        if "sigs_long_exit_reason" in signals.df_signals.columns:
            val = signals.df_signals["sigs_long_exit_reason"].iloc[-1]
            long_exit_reason = val if val and not pd.isna(val) else ""
        if "sigs_short_exit_reason" in signals.df_signals.columns:
            val = signals.df_signals["sigs_short_exit_reason"].iloc[-1]
            short_exit_reason = val if val and not pd.isna(val) else ""

        # --- Step 7: entry detection — bar N IS the shift(1) for the next bar ---
        # The threshold check at hypothetical bar N+1 uses:
        #   shift(1) = bar N (just built), shift(2) = N-1, shift(3) = N-2
        # All available in the cache right now.
        # If conditions pass, enter at market ≈ bar N+1's Open (matching backtest).
        ema_fast = f"EMA_{EMA[0]}"
        ema_slow = f"EMA_{EMA[-1]}"
        vwma_col = f"VWMA_{VWMA[0]}"

        long_entry = False
        short_entry = False

        if len(self._cached_signal_df) >= 4:
            b1 = self._cached_signal_df.iloc[-1]  # bar N  = shift(1)
            b2 = self._cached_signal_df.iloc[-2]  # bar N-1 = shift(2)
            b3 = self._cached_signal_df.iloc[-3]  # bar N-2 = shift(3)

            gap1 = b1[ema_fast] - b1[vwma_col]
            gap2 = b2[ema_fast] - b2[vwma_col]
            gap3 = b3[ema_fast] - b3[vwma_col]
            delta_new = gap1 - gap2
            delta_old = gap2 - gap3

            # Long: EMA below VWMA, gap closing + accelerating upward
            long_side = (
                b1[ema_fast] < b1[vwma_col] and
                b2[ema_fast] < b2[vwma_col] and
                b3[ema_fast] < b3[vwma_col]
            )
            long_within = abs(gap1) < self.long_threshold
            long_closing = delta_new > 0
            long_accel = (delta_new > delta_old) and (delta_old > 0)
            long_setup = (b1[ema_fast] < b1[vwma_col]) and (b1[ema_fast] < b1[ema_slow])
            long_entry = bool(long_side and long_within and long_closing and long_accel and long_setup)

            # Short: EMA above VWMA, gap closing + accelerating downward
            short_side = (
                b1[ema_fast] > b1[vwma_col] and
                b2[ema_fast] > b2[vwma_col] and
                b3[ema_fast] > b3[vwma_col]
            )
            short_within = abs(gap1) < self.short_threshold
            short_closing = delta_new < 0
            short_accel = (delta_new < delta_old) and (delta_old < 0)
            short_setup = (b1[ema_fast] > b1[vwma_col]) and (b1[ema_fast] > b1[ema_slow])
            short_entry = bool(short_side and short_within and short_closing and short_accel and short_setup)

        latest = slice_with_ind.iloc[-1]
        latest_idx = slice_with_ind.index[-1]

        return {
            "timestamp": latest_idx,
            "bar": latest,
            "long_entry": long_entry,
            "long_exit": bool(long_exits.iloc[-1]) if len(long_exits) > 0 else False,
            "short_entry": short_entry,
            "short_exit": bool(short_exits.iloc[-1]) if len(short_exits) > 0 else False,
            "long_exit_reason": long_exit_reason,
            "short_exit_reason": short_exit_reason,
        }
