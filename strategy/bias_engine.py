"""Phase 3 — Daily bias engine.

Consumes a warmed-up :class:`~strategy.indicators.DailyIndicators` snapshot
(Phase 2) and emits a :class:`BiasResult` describing the directional bias for
the day a session is about to open. Five base signals (EMA50 vs price, RSI,
MACD histogram, prior-day high/low, price vs session VWAP) each cast a
bullish / bearish / abstain vote; an ADX > threshold "booster" adds one vote
to whichever side strictly leads. The tallied scores map to a five-level :class:`BiasLabel` via the
thresholds defined as constants at the top of this file. Equal scores are
broken by EMA50 vs reference price.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # import only for type hints — avoids any circular-import risk
    from strategy.indicators import DailyIndicators


class BiasNotReadyError(Exception):
    """Raised when DailyIndicators has not warmed up enough to compute a bias."""


# --- Bias engine configuration -------------------------------------------

STRONG_THRESHOLD = 5            # bullish_score or bearish_score >= 5
WEAK_THRESHOLD = 3              # bullish_score or bearish_score >= 3 (and < 5)
ADX_TREND_THRESHOLD = 20.0      # ADX > this enables the booster vote
# Nautilus RelativeStrengthIndex returns a 0.0–1.0 value, NOT 0–100, so the
# neutral midpoint is 0.5. (Comparing against 50.0 made RSI vote bearish every
# session — the value can never exceed 1.0.)
RSI_NEUTRAL = 0.5               # RSI > this is bullish, < is bearish
MACD_HISTOGRAM_NEUTRAL = 0.0    # histogram > 0 is bullish

# Reference price used for the EMA50 and PDH/PDL comparisons. Per the Phase 3
# blueprint this defaults to the prior daily close until the spec confirms an
# alternative (session-open tick / yesterday's high-low midpoint).
_REF_PRICE_KEY = "prev_close"


class BiasLabel(Enum):
    STRONG_BULLISH = "strong_bullish"
    WEAK_BULLISH = "weak_bullish"
    NEUTRAL = "neutral"
    WEAK_BEARISH = "weak_bearish"
    STRONG_BEARISH = "strong_bearish"


@dataclass(frozen=True)
class BiasResult:
    session_date: date
    symbol: str
    label: BiasLabel
    bullish_score: int
    bearish_score: int
    tie_broken: bool
    adx_active: bool
    votes: dict[str, str] = field(default_factory=dict)
    indicators_snapshot: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        """One-line log form, e.g. ``EURUSD 2026-05-19 STRONG_BULLISH (5-0)``."""
        return (
            f"{self.symbol} {self.session_date} {self.label.name} "
            f"({self.bullish_score}-{self.bearish_score})"
        )

    def __repr__(self) -> str:
        return f"BiasResult<{self.summary()}>"


# --- Base voting helpers (pure, no state, no logging) --------------------

def _vote_ema50(ref_price: float, ema50: float) -> str:
    if ref_price > ema50:
        return "bullish"
    if ref_price < ema50:
        return "bearish"
    return "abstain"


def _vote_rsi(rsi: float) -> str:
    if rsi > RSI_NEUTRAL:
        return "bullish"
    if rsi < RSI_NEUTRAL:
        return "bearish"
    return "abstain"


def _vote_macd(macd_hist: float) -> str:
    if macd_hist > MACD_HISTOGRAM_NEUTRAL:
        return "bullish"
    if macd_hist < MACD_HISTOGRAM_NEUTRAL:
        return "bearish"
    return "abstain"


def _vote_pdh_pdl(
    current_price: float | None, prev_high: float, prev_low: float
) -> str:
    """Breakout signal: today's live price vs yesterday's high/low.

    Must use the *current* price, not the prior daily close — a day's close
    is always inside its own [low, high] range, so feeding prev_close here
    makes the vote abstain every single session.
    """
    if current_price is None:
        return "abstain"
    if current_price > prev_high:
        return "bullish"
    if current_price < prev_low:
        return "bearish"
    return "abstain"  # inside [prev_low, prev_high] inclusive


def _vote_vwap(current_price: float | None, vwap: float | None) -> str:
    """VWAP signal: current session price vs session VWAP.

    Uses the *live* entry-bar close, not the prior daily close — the whole
    point of VWAP is where price sits within the current session. Comparing
    yesterday's close to today's VWAP makes this vote a lagging duplicate of
    the EMA50 / PDH-PDL voters, which already use ``prev_close``.
    """
    if vwap is None or current_price is None:  # missing input -> sit out
        return "abstain"
    if current_price > vwap:
        return "bullish"
    if current_price < vwap:
        return "bearish"
    return "abstain"


def _classify(
    bullish_score: int,
    bearish_score: int,
    ref_price: float,
    ema50: float,
) -> tuple[BiasLabel, bool]:
    """Map scores to a label, returning ``(label, tie_broken)``.

    NOTE: the equal-scores tie check intentionally precedes the threshold
    ladder. This deviates from the manager's pseudocode ordering (which put
    the tie check last) but matches its intent — do not "fix" it back.
    """
    if bullish_score == bearish_score:
        if ref_price > ema50:
            return (BiasLabel.WEAK_BULLISH, True)
        return (BiasLabel.WEAK_BEARISH, True)
    if bullish_score >= STRONG_THRESHOLD:
        return (BiasLabel.STRONG_BULLISH, False)
    if bullish_score >= WEAK_THRESHOLD:
        return (BiasLabel.WEAK_BULLISH, False)
    if bearish_score >= STRONG_THRESHOLD:
        return (BiasLabel.STRONG_BEARISH, False)
    if bearish_score >= WEAK_THRESHOLD:
        return (BiasLabel.WEAK_BEARISH, False)
    return (BiasLabel.NEUTRAL, False)


class BiasEngine:
    """Stateless engine — one :meth:`compute` call per symbol per session."""

    def __init__(self) -> None:
        pass

    def compute(
        self,
        daily_indicators: "DailyIndicators",
        symbol: str,
        session_date: date,
        vwap: float | None = None,
        current_price: float | None = None,
    ) -> BiasResult:
        """``vwap`` is the current session VWAP (e.g. ``SessionVWAP.effective``);
        ``current_price`` is the live entry-bar close used for the VWAP vote.

        The tie check intentionally precedes the threshold ladder.

        The pseudocode put the tie check last (override after the
        ladder), but that ordering makes the `tie_broken` flag harder to
        report correctly: a 3-3 tie would first match WEAK_BULLISH in the
        ladder (tie_broken=False) and only then get overridden by the tie
        block, leaving the audit trail showing tie_broken=False for a
        genuinely tied score.

        Checking ties first guarantees `tie_broken=True` whenever scores
        were actually equal. The final label is identical to the
        flow in every case — only the audit-trail bookkeeping differs
        """
        if not daily_indicators.initialized:
            raise BiasNotReadyError(
                f"DailyIndicators not warmed up for {symbol} on {session_date}"
            )

        snapshot = daily_indicators.snapshot()
        ref_price = snapshot[_REF_PRICE_KEY]

        votes = {
            "ema50": _vote_ema50(ref_price, snapshot["ema50"]),
            "rsi": _vote_rsi(snapshot["rsi"]),
            "macd": _vote_macd(snapshot["macd_hist"]),
            "pdh_pdl": _vote_pdh_pdl(
                current_price, snapshot["prev_high"], snapshot["prev_low"]
            ),
            "vwap": _vote_vwap(current_price, vwap),
        }

        bullish_score = sum(1 for v in votes.values() if v == "bullish")
        bearish_score = sum(1 for v in votes.values() if v == "bearish")

        adx_active = bool(snapshot["adx_active"])
        if adx_active:
            if bullish_score > bearish_score:
                bullish_score += 1
            elif bearish_score > bullish_score:
                bearish_score += 1

        label, tie_broken = _classify(
            bullish_score, bearish_score, ref_price, snapshot["ema50"]
        )

        return BiasResult(
            session_date=session_date,
            symbol=symbol,
            label=label,
            bullish_score=bullish_score,
            bearish_score=bearish_score,
            tie_broken=tie_broken,
            adx_active=adx_active,
            votes=votes,
            indicators_snapshot={
                **snapshot, "vwap": vwap, "current_price": current_price
            },
        )
