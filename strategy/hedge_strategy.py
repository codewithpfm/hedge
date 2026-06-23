"""Phase 4 — Dual Position Bias Strategy.

Implements the blueprint in *Dual Position.pdf*: at every session open the
strategy opens **both** a long and a short position, then uses the daily
:class:`~strategy.bias_engine.BiasEngine` (Phase 3) to size the SL/TP of each
leg so the book leans into the dominant direction. Every leg carries an
internal (broker-side-agnostic) ATR-based stop and target and is force-closed
once it has been held longer than ``max_hold_hours`` — there is no
session-close flatten, so a position can outlive the session that opened it.

Execution flow (PDF §4 / §8)::

    Session open  (Friday sessions skipped — would straddle the weekend)
      └─ optional delay (VWAP stabilisation)
           └─ compute daily indicators + session VWAP
                └─ score bias  (BiasEngine)
                     └─ volatility filter  (ATR < threshold -> skip)
                          └─ open long + short  (equal size,
                             halved when ADX inactive / ranging)
                               └─ per-bar SL / TP / max-hold monitor

The two legs must be able to coexist, so the instrument/venue is expected to
run under an MT5 hedging account (OMS HEDGING). Legs are tracked explicitly by
``PositionId`` via ``on_position_opened`` rather than through net portfolio
state, so the logic does not depend on netting behaviour.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone

import pandas as pd
from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.trading.strategy import Strategy

from config import SESSION
from utils.maps import SESSION_HOURS, normalize, session_bucket
from strategy.bias_engine import BiasEngine, BiasLabel, BiasNotReadyError
from strategy.indicators import DailyIndicators, SessionVWAP
from utils.instrument_specs import get_instrument_spec

# ── SL/TP ATR multiples per bias label (PDF §6) ──────────────────────────
# Maps a BiasLabel to (long_sl, long_tp, short_sl, short_tp) in ATR units.
# NEUTRAL is not specified in the blueprint; we fall back to the most
# conservative symmetric weak setting (0.25 / 0.25 both legs).
_SLTP_BY_BIAS: dict[BiasLabel, tuple[float, float, float, float]] = {
    BiasLabel.STRONG_BULLISH: (0.50, 1.00, 0.25, 0.50),
    BiasLabel.WEAK_BULLISH:   (0.25, 0.50, 0.25, 0.25),
    BiasLabel.STRONG_BEARISH: (0.25, 0.50, 0.50, 1.00),
    BiasLabel.WEAK_BEARISH:   (0.25, 0.25, 0.25, 0.50),
    BiasLabel.NEUTRAL:        (0.25, 0.25, 0.25, 0.25),
}


class HedgeStrategyConfig(StrategyConfig, kw_only=True):
    instrument_id: str
    leverage: float
    session: str = SESSION
    # PDF §4 Step 2 — wait this many minutes after the open before entering
    # (recommended 15–30 for VWAP stability).
    entry_delay_mins: int = 15
    # 1M bars are aggregated into these for the rolling session VWAP (PDF §3.1).
    vwap_tf_mins: int = 30
    # ATR risk-based sizing — fraction of free balance risked per leg over
    # one ATR of adverse price movement (PDF §7 sizing model).
    risk_percent: float = 0.01
    # PDF §9 volatility filter — skip the session if previous-day ATR is below
    # this absolute price threshold. 0.0 disables the filter.
    atr_min_threshold: float = 0.0
    # Force-close any leg still open this many hours after entry (catches the
    # case where neither SL nor TP is hit and session-close also misses it).
    max_hold_hours: float = 23.0


class _Leg:
    """One side of the dual position with its internal ATR stop/target."""

    __slots__ = ("side", "position_id", "entry", "sl", "tp", "quantity", "entry_ts")

    def __init__(self, side: OrderSide):
        self.side = side
        self.position_id = None
        self.entry = 0.0
        self.sl = 0.0
        self.tp = 0.0
        self.quantity = None
        self.entry_ts: datetime | None = None

    @property
    def is_long(self) -> bool:
        return self.side == OrderSide.BUY


class HedgeStrategy(Strategy):
    """Dual-position, bias-weighted intraday strategy (see module docstring)."""

    def __init__(self, config: HedgeStrategyConfig):
        super().__init__(config)
        self.instrument_id_str = config.instrument_id
        self.leverage = config.leverage
        # Per-symbol pip / contract spec driving ATR risk-based sizing.
        # Looked up here so an unknown ticker fails fast at construction.
        self._spec = get_instrument_spec(config.instrument_id)
        self.session = normalize(config.session)
        self.entry_delay = timedelta(minutes=config.entry_delay_mins)

        self._open_hour = SESSION_HOURS[self.session]["open"]

        # ── Indicator stack (Phases 2 & 3) ──
        self.daily = DailyIndicators()
        self.vwap = SessionVWAP(self.session)
        self.bias_engine = BiasEngine()

        # ── Per-session state ──
        self._session_bucket = None      # date of the active session
        self._entered = False            # opened the dual position this session
        self._skip_session = False       # Friday / volatility filter tripped
        self._long = _Leg(OrderSide.BUY)
        self._short = _Leg(OrderSide.SELL)

        # ── Manual aggregation buffers ──
        self._vwap_bar = None
        self._daily_bar = None
        self._daily_bar_day = None

        # ── Recording for TVCharts parity ──
        self.recorded_data = []

        # ── Per-position trade log (votes + indicators, one row per leg) ──
        self.trades_log = []
        self._pending_bias_record = None         # bias snapshot for the open session
        self._bias_by_position = {}              # position_id -> bias snapshot
        self._exit_reason_by_position = {}        # position_id -> close reason

        self._instrument_id = None
        self._instrument = None

    # ─────────────────────────────────────────────────────────
    # Lifecycle
    # ─────────────────────────────────────────────────────────
    def on_start(self):
        self._instrument_id = InstrumentId.from_str(self.instrument_id_str)
        self._instrument = self.cache.instrument(self._instrument_id)
        self.subscribe_bars(
            BarType.from_str(f"{self.instrument_id_str}-1-MINUTE-LAST-EXTERNAL")
        )

    # ─────────────────────────────────────────────────────────
    # 1-Minute bar handler  (PDF §8 flowchart driver)
    # ─────────────────────────────────────────────────────────
    def on_bar(self, bar: Bar):
        ts = datetime.fromtimestamp(bar.ts_event / 1e9, tz=timezone.utc)

        # 1. Keep indicators warm (VWAP is fed aggregated 30M bars, not 1M).
        self._aggregate_vwap(bar, ts)
        self._aggregate_daily(bar, ts)

        # 2. Detect a new trading session.
        bucket = session_bucket(ts, self.session)
        if bucket != self._session_bucket:
            self._on_new_session(bucket)

        minutes_in = self._minutes_into_session(ts, bucket)

        # 3. Per-bar exit monitor — SL/TP + max-hold. There is no session-close
        # flatten: a leg is held until SL, TP, or max_hold_hours, so this must
        # run whenever a leg is open — including after the opening session has
        # rolled over (when _entered has already been reset to False).
        if self._long.position_id or self._short.position_id:
            self._check_leg_sltp(self._long, bar.close.as_double())
            self._check_leg_sltp(self._short, bar.close.as_double())
            self._check_leg_max_hold(self._long, ts)
            self._check_leg_max_hold(self._short, ts)

        # 4. Entry — once per session, after the delay filter. Blocked while a
        # leg from a prior session is still open: each _Leg tracks a single
        # position_id, so a new entry would orphan the unclosed one.
        if (
            not self._entered
            and not self._skip_session
            and self._long.position_id is None
            and self._short.position_id is None
            and minutes_in >= self.entry_delay.total_seconds() / 60
        ):
            self._try_enter(bar, ts, bucket)

    # ─────────────────────────────────────────────────────────
    # Session bookkeeping
    # ─────────────────────────────────────────────────────────
    def _on_new_session(self, bucket):
        # Pure bookkeeping — positions are never closed on a session boundary.
        # A leg outliving its session is closed by max-hold; the entry guard
        # blocks a new dual position while one is still open.
        self._session_bucket = bucket
        self._entered = False
        # Skip Friday-opening sessions: with max-hold closing (no session-close
        # flatten), a Friday entry would be carried into the forex weekend.
        self._skip_session = bucket.weekday() == 4

    def _minutes_into_session(self, ts: datetime, bucket) -> float:
        """Minutes elapsed since this session's open (shift-back trick)."""
        shifted = ts - timedelta(hours=self._open_hour)
        session_start = datetime.combine(
            bucket, time(0), tzinfo=timezone.utc
        )
        return (shifted - session_start).total_seconds() / 60.0

    # ─────────────────────────────────────────────────────────
    # Entry  (PDF §4 Step 3 / §5 bias / §6 SL-TP / §9 filters)
    # ─────────────────────────────────────────────────────────
    def _try_enter(self, bar: Bar, ts: datetime, bucket):
        if not self.daily.initialized:
            return  # daily indicators not warmed up yet

        try:
            bias = self.bias_engine.compute(
                self.daily,
                self.instrument_id_str,
                bucket,
                vwap=self.vwap.effective,
                current_price=bar.close.as_double(),
            )
        except BiasNotReadyError:
            return

        snap = self.daily.snapshot()
        atr = float(snap["atr"])

        # PDF §9 volatility filter — skip the whole session.
        cfg = self.config
        if cfg.atr_min_threshold > 0.0 and atr < cfg.atr_min_threshold:
            self.log.info(
                f"[{self.instrument_id_str}] ATR {atr:.5f} < "
                f"{cfg.atr_min_threshold} — skipping session {bucket}"
            )
            self._skip_session = True
            return

        long_sl_m, long_tp_m, short_sl_m, short_tp_m = _SLTP_BY_BIAS[bias.label]
        price = bar.close.as_double()

        qty = self._position_qty(atr)
        if qty is None:
            return

        self.log.info(
            f"[{self.instrument_id_str}] {bias.summary()} | ATR={atr:.5f} "
            f"adx_active={bias.adx_active} -> dual entry qty={qty}"
        )

        # Stash the ATR offsets; concrete SL/TP prices are set from the actual
        # fill in on_position_opened.
        self._long.sl, self._long.tp = long_sl_m * atr, long_tp_m * atr
        self._short.sl, self._short.tp = short_sl_m * atr, short_tp_m * atr

        # Snapshot the bias votes + indicator values that drove this entry.
        # Both legs share it; bound to each position_id in on_position_opened.
        # ref_price is what the bias voters compare against (prev daily close).
        self._pending_bias_record = {
            "session_date": str(bucket),
            "bias": bias.label.name,
            "bullish_score": bias.bullish_score,
            "bearish_score": bias.bearish_score,
            "tie_broken": bias.tie_broken,
            "adx_active": bias.adx_active,
            "vote_ema50": bias.votes.get("ema50"),
            "vote_rsi": bias.votes.get("rsi"),
            "vote_macd": bias.votes.get("macd"),
            "vote_pdh_pdl": bias.votes.get("pdh_pdl"),
            "vote_vwap": bias.votes.get("vwap"),
            "atr": atr,
            "ema50": snap["ema50"],
            "rsi": snap["rsi"],
            "macd_hist": snap["macd_hist"],
            "adx": snap["adx"],
            "di_pos": snap["di_pos"],
            "di_neg": snap["di_neg"],
            "prev_high": snap["prev_high"],
            "prev_low": snap["prev_low"],
            "prev_close": snap["prev_close"],
            "ref_price": snap["prev_close"],
            "vwap": self.vwap.effective,
            "entry_close": price,
        }

        self._submit(OrderSide.BUY, qty)
        self._submit(OrderSide.SELL, qty)
        self._entered = True

        self.recorded_data.append({
            "Datetime": pd.to_datetime(bar.ts_event, unit="ns", utc=True),
            "close": price,
            "bias": bias.label.name,
            "bullish_score": bias.bullish_score,
            "bearish_score": bias.bearish_score,
            "adx_active": bias.adx_active,
            "atr": atr,
            "vwap": self.vwap.effective,
            "ema50": snap["ema50"],
            "long_entries": True,
            "short_entries": True,
        })

    # ─────────────────────────────────────────────────────────
    # Position sizing  (ATR risk-based model, equal size both legs)
    # ─────────────────────────────────────────────────────────
    def _position_qty(self, atr: float):
        """ATR risk-based sizing (standard MT5 risk model) — each leg risks
        ``risk_percent`` of the free balance over one ATR of adverse movement::

            risk_amount = balance * risk_percent
            sl_pips     = atr / pip_size
            lots        = risk_amount / (sl_pips * pip_value)
            units       = lots * contract_size

        Per-symbol ``pip_size`` / ``pip_value`` / ``contract_size`` come from
        :mod:`utils.instrument_specs`, so switching from a forex pair to gold
        (``XAUUSD``) is a table lookup — the formula is unchanged. ``balance``
        is read in the instrument's quote currency to match the currency
        ``pip_value`` is denominated in. Returns ``None`` if ATR is
        non-positive or the size is below the broker's minimum lot.
        """
        if atr <= 0.0:
            return None
        spec = self._spec
        account = self.portfolio.account(self._instrument_id.venue)
        # Multi-currency margin account: must specify which currency to size
        # against. Use the quote currency so risk_amount and pip_value share it.
        balance = account.balance_free(self._instrument.quote_currency).as_double()

        risk_amount = balance * self.config.risk_percent
        sl_pips = atr / spec.pip_size
        lots = risk_amount / (sl_pips * spec.pip_value)
        if lots < spec.min_lot:
            self.log.warning(
                f"[{self.instrument_id_str}] computed {lots:.4f} lots < "
                f"min {spec.min_lot} (balance={balance:.2f}, atr={atr:.5f}, "
                f"risk%={self.config.risk_percent}) — skipping entry"
            )
            return None
        units = int(lots * spec.contract_size)
        return self._instrument.make_qty(units)

    # ─────────────────────────────────────────────────────────
    # Internal SL / TP  (PDF §7 — not delegated to the broker)
    # ─────────────────────────────────────────────────────────
    def _check_leg_sltp(self, leg: _Leg, price: float):
        if leg.position_id is None:
            return
        if leg.is_long:
            if price <= leg.entry - leg.sl:
                self._close_leg(leg, "SL")
            elif price >= leg.entry + leg.tp:
                self._close_leg(leg, "TP")
        else:
            if price >= leg.entry + leg.sl:
                self._close_leg(leg, "SL")
            elif price <= leg.entry - leg.tp:
                self._close_leg(leg, "TP")

    def _check_leg_max_hold(self, leg: _Leg, ts: datetime):
        if leg.position_id is None or leg.entry_ts is None:
            return
        if ts - leg.entry_ts >= timedelta(hours=self.config.max_hold_hours):
            self._close_leg(leg, f"max-hold {self.config.max_hold_hours}h")

    # ─────────────────────────────────────────────────────────
    # Order helpers
    # ─────────────────────────────────────────────────────────
    def _submit(self, side: OrderSide, qty):
        order = self.order_factory.market(
            instrument_id=self._instrument_id,
            order_side=side,
            quantity=qty,
        )
        self.submit_order(order)

    def _close_leg(self, leg: _Leg, reason: str):
        if leg.position_id is None:
            return
        pos = self.cache.position(leg.position_id)
        if pos is None or pos.is_closed:
            leg.position_id = None
            leg.entry_ts = None
            return
        self.log.info(
            f"[{self.instrument_id_str}] closing "
            f"{'LONG' if leg.is_long else 'SHORT'} leg ({reason})"
        )
        # Stash the reason before clearing — on_position_closed fires later,
        # by which point leg.position_id is gone.
        self._exit_reason_by_position[leg.position_id] = reason
        # In OmsType.HEDGING a plain opposite-side market order opens a NEW
        # position instead of flattening this one. close_position() targets the
        # specific position_id and closes it.
        self.close_position(pos)
        leg.position_id = None
        leg.entry_ts = None

    # ─────────────────────────────────────────────────────────
    # Position events — bind fills to legs and finalise SL/TP prices
    # ─────────────────────────────────────────────────────────
    def on_position_opened(self, event):
        pos = self.cache.position(event.position_id)
        if pos is None or pos.instrument_id != self._instrument_id:
            return
        leg = self._long if pos.is_long else self._short
        leg.position_id = event.position_id
        leg.entry = float(pos.avg_px_open)
        leg.entry_ts = datetime.fromtimestamp(event.ts_event / 1e9, tz=timezone.utc)
        # Bind this session's bias snapshot to the position so it can be
        # written into the trade log when the position closes.
        if self._pending_bias_record is not None:
            self._bias_by_position[event.position_id] = self._pending_bias_record
        # .sl/.tp hold ATR *distances* set in _try_enter; _check_leg_sltp
        # compares price against entry ± distance, so nothing to convert here.
        self.log.info(
            f"[{self.instrument_id_str}] "
            f"{'LONG' if leg.is_long else 'SHORT'} filled @ {leg.entry:.5f} "
            f"SLΔ={leg.sl:.5f} TPΔ={leg.tp:.5f}"
        )

    def on_position_closed(self, event):
        pos = self.cache.position(event.position_id)
        if pos is not None and pos.instrument_id == self._instrument_id:
            self._record_closed_trade(pos, event.position_id)

        if self._long.position_id == event.position_id:
            self._long.position_id = None
            self._long.entry_ts = None
        if self._short.position_id == event.position_id:
            self._short.position_id = None
            self._short.entry_ts = None

    def _record_closed_trade(self, pos, position_id) -> None:
        """Append one per-position row (entry/exit + bias votes + indicators)
        to ``trades_log`` — consumed by main.py to write trades.parquet.
        """
        bias_rec = self._bias_by_position.get(position_id, {})
        row = {
            "entry_date": pd.to_datetime(pos.ts_opened, unit="ns", utc=True),
            "exit_date": pd.to_datetime(pos.ts_closed, unit="ns", utc=True),
            "entry_price": float(pos.avg_px_open),
            "exit_price": float(pos.avg_px_close),
            "type": "long" if pos.entry == OrderSide.BUY else "short",
            "size": float(pos.peak_qty),
            "pnl": pos.realized_pnl.as_double(),
            "return": float(pos.realized_return),
            "exit_reason": self._exit_reason_by_position.get(position_id, "unknown"),
        }
        row.update(bias_rec)
        self.trades_log.append(row)

    # ─────────────────────────────────────────────────────────
    # Bar aggregation
    # ─────────────────────────────────────────────────────────
    def _aggregate_vwap(self, bar: Bar, ts: datetime):
        """1M -> ``vwap_tf_mins`` bars fed to :class:`SessionVWAP`."""
        tf = self.config.vwap_tf_mins
        ts_mins = bar.ts_event // (60 * 1_000_000_000)
        is_closing = (ts_mins + 1) % tf == 0

        if self._vwap_bar is None:
            self._vwap_bar = {
                "open": bar.open, "high": bar.high, "low": bar.low,
                "close": bar.close, "volume": bar.volume,
                "ts_event": bar.ts_event,
            }
        else:
            v = self._vwap_bar
            v["high"] = max(v["high"], bar.high)
            v["low"] = min(v["low"], bar.low)
            v["close"] = bar.close
            v["volume"] += bar.volume

        if is_closing:
            v = self._vwap_bar
            self.vwap.handle_bar(Bar(
                bar_type=bar.bar_type,
                open=v["open"], high=v["high"], low=v["low"],
                close=v["close"], volume=v["volume"],
                ts_event=v["ts_event"], ts_init=v["ts_event"],
            ))
            self._vwap_bar = None

    def _aggregate_daily(self, bar: Bar, ts: datetime):
        """1M -> 1D bars fed to :class:`DailyIndicators` on day rollover."""
        day = ts.date()
        if self._daily_bar is None:
            self._daily_bar_day = day
            self._daily_bar = {
                "open": bar.open, "high": bar.high, "low": bar.low,
                "close": bar.close, "volume": bar.volume,
                "ts_event": bar.ts_event,
            }
            return

        if day != self._daily_bar_day:
            d = self._daily_bar
            self.daily.handle_bar(Bar(
                bar_type=bar.bar_type,
                open=d["open"], high=d["high"], low=d["low"],
                close=d["close"], volume=d["volume"],
                ts_event=d["ts_event"], ts_init=d["ts_event"],
            ))
            self._daily_bar_day = day
            self._daily_bar = {
                "open": bar.open, "high": bar.high, "low": bar.low,
                "close": bar.close, "volume": bar.volume,
                "ts_event": bar.ts_event,
            }
        else:
            d = self._daily_bar
            d["high"] = max(d["high"], bar.high)
            d["low"] = min(d["low"], bar.low)
            d["close"] = bar.close
            d["volume"] += bar.volume
