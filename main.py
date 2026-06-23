import argparse
import cProfile
import json
import logging
import pickle
import pstats
import sys
import time
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd

from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.backtest.models import FillModel, FixedFeeModel
from nautilus_trader.config import BacktestEngineConfig, LoggingConfig
from nautilus_trader.core.nautilus_pyo3 import (
    AvgLoser, AvgWinner, Expectancy, LongRatio, MaxLoser, MaxWinner,
    MinLoser, MinWinner, ProfitFactor, ReturnsAverage, ReturnsAverageLoss,
    ReturnsAverageWin, ReturnsVolatility, RiskReturnRatio, SharpeRatio,
    SortinoRatio, WinRate,
)
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import AccountType, OmsType
from nautilus_trader.model.identifiers import TraderId, Venue
from nautilus_trader.model.objects import Money
from nautilus_trader.persistence.wranglers import BarDataWrangler

from config import (
    ATR_MIN_THRESHOLD,
    CASH,
    ENDDATE,
    ENTRY_DELAY_MINS,
    FEES,
    LEVERAGE,
    MAX_HOLD_HOURS,
    OUTPUT_DIR,
    RISK_PERCENT,
    SESSION,
    STARTDATE,
    TICKER,
    VWAP_TF_MINS,
)
from storelib.fetcher import Fetcher
from strategy.hedge_strategy import HedgeStrategy, HedgeStrategyConfig
from utils.nautilus_converter import setup_forex_instrument

# ── Constants ────────────────────────────────────────────────────────────
WARMUP_DAYS = 60
SIM_VENUE = Venue("SIM")

# Rough USD→quote spot rates — seed the simulated account in the instrument's
# quote currency so `account.balance_free(quote)` resolves. Sizing scaffold
# only, not a P&L input — exact rates not required.
_USD_TO_QUOTE_SEED_RATE = {
    "USD": 1.0, "JPY": 157.0, "EUR": 0.92, "GBP": 0.79,
    "AUD": 1.52, "CHF": 0.90, "CAD": 1.37, "NZD": 1.66,
}


# ─────────────────────────────────────────────────────────────────────────
# Bar loading + cache
# ─────────────────────────────────────────────────────────────────────────
def _wrangle_bars(df: pd.DataFrame, instrument) -> list:
    """Convert a Polygon DataFrame into a list of Nautilus ``Bar`` objects.

    Polygon DataFrames come with ``Open/High/Low/Close/Volume`` capitalised
    columns and a tz-aware ``Datetime`` index (see ``storelib/urls.py``).
    ``BarDataWrangler.process`` wants lowercase columns, so we normalise.
    """
    if df.empty:
        raise RuntimeError("Fetcher returned an empty DataFrame")

    df = df.rename(columns=str.lower)
    keep = ["open", "high", "low", "close"]
    if "volume" in df.columns:
        keep.append("volume")
    df = df[keep]

    bar_type = BarType.from_str(f"{instrument.id}-1-MINUTE-LAST-EXTERNAL")
    # Vectorized in-memory wrangle — faster than the row-by-row disk-catalog build.
    wrangler = BarDataWrangler(bar_type=bar_type, instrument=instrument)
    return wrangler.process(df)


def _fetch_bars(ticker: str, instrument, log: logging.Logger) -> list:
    """Fetch raw 1M bars via ``Fetcher`` (parquet-cached under ``.futures/``)
    and wrangle them into Nautilus ``Bar`` objects. Pads the start date by
    ``WARMUP_DAYS`` so EMA50 / VWMA bootstrap before the live test window.
    """
    warmup_start = (
        pd.Timestamp(STARTDATE) - pd.Timedelta(days=WARMUP_DAYS)
    ).strftime("%Y-%m-%d")
    log.info(f"[fetch] {ticker}: {warmup_start} -> {ENDDATE} "
             f"(warmup pad: {WARMUP_DAYS}d)")
    t0 = time.perf_counter()
    fetcher = Fetcher(dir="futures")
    df = fetcher.get(ticker, warmup_start, f"{ENDDATE}")
    df = df.dropna()
    df.index.names = ["Datetime"]
    log.info(
        f"[fetch] {len(df):,} 1M rows in {time.perf_counter()-t0:.1f}s "
        f"({df.index.min()} -> {df.index.max()})"
    )

    t0 = time.perf_counter()
    bars = _wrangle_bars(df, instrument)
    log.info(
        f"[wrangle] {len(bars):,} bars in {time.perf_counter()-t0:.1f}s"
    )
    return bars


# ─────────────────────────────────────────────────────────────────────────
# Setup helpers
# ─────────────────────────────────────────────────────────────────────────
def _setup_run_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = OUTPUT_DIR / f"{TICKER}_{SESSION}_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "ticker": TICKER,
        "session": SESSION,
        "start": STARTDATE,
        "end": ENDDATE,
        "starting_balance_usd": CASH,
        "leverage": LEVERAGE,
        "risk_percent": RISK_PERCENT,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    (out_dir / "run_meta.json").write_text(json.dumps(meta, indent=2))
    return out_dir


def _setup_python_logging(out_dir: Path) -> logging.Logger:
    log = logging.getLogger("backtest")
    log.setLevel(logging.INFO)
    log.handlers.clear()

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    log.addHandler(sh)

    fh = logging.FileHandler(out_dir / "main.log", encoding="utf-8")
    fh.setFormatter(fmt)
    log.addHandler(fh)
    return log


def _build_engine(out_dir: Path) -> BacktestEngine:
    cfg = BacktestEngineConfig(
        trader_id=TraderId("BACKTESTER-001"),
        logging=LoggingConfig(
            log_level="WARNING",        # quiet stdout
            log_level_file="INFO",       # full audit trail on disk
            log_directory=str(out_dir),
            log_file_format="json",      # greppable
            bypass_logging=False,
        ),
    )
    return BacktestEngine(config=cfg)


def _build_fill_model() -> FillModel:
    # Placeholder cost model — realistic slippage deferred.
    return FillModel(prob_fill_on_limit=1.0, prob_slippage=0.0, random_seed=42)


def _register_venue(
    engine: BacktestEngine, fill_model: FillModel, instrument, log
) -> None:
    # The strategy sizes via `account.balance_free(instrument.quote_currency)`,
    # so the venue must be seeded in that currency. CASH is USD-denominated;
    # convert at a rough USD→quote rate (sizing-only, not P&L).
    quote = instrument.quote_currency
    rate = _USD_TO_QUOTE_SEED_RATE.get(quote.code, 1.0)
    seed_balance = CASH * rate
    # Flat per-order commission in the instrument's quote currency. One leg =
    # open + close = 2 orders = 2*FEES; a session (dual leg) = 4 orders = 4*FEES.
    fee_model = FixedFeeModel(
        commission=Money(FEES, quote),
        charge_commission_once=True,
    )
    engine.add_venue(
        venue=SIM_VENUE,
        oms_type=OmsType.HEDGING,           # non-negotiable for dual-leg
        account_type=AccountType.MARGIN,
        base_currency=None,
        starting_balances=[Money(seed_balance, quote)],
        fill_model=fill_model,
        fee_model=fee_model,
        default_leverage=Decimal(LEVERAGE),
    )
    log.info(
        f"[venue] OmsType=HEDGING leverage={LEVERAGE}x "
        f"balance={seed_balance:,.2f} {quote.code} (~{CASH:,} USD @ {rate}) "
        f"fee={FEES} {quote.code}/order"
    )


def _register_instrument_and_data(engine: BacktestEngine, instrument, log) -> None:
    engine.add_instrument(instrument)
    log.info(f"[instrument] {instrument.id} multiplier={instrument.multiplier}")

    bars = _fetch_bars(f"C:{TICKER}", instrument, log)

    engine.add_data(bars)


def _register_strategy(engine: BacktestEngine, instrument, log) -> HedgeStrategy:
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
    strat = HedgeStrategy(config=cfg)
    engine.add_strategy(strat)
    log.info(f"[strategy] {type(strat).__name__} risk_percent={RISK_PERCENT}")
    return strat


# ─────────────────────────────────────────────────────────────────────────
# Profiling
# ─────────────────────────────────────────────────────────────────────────
def _run_with_profile(engine: BacktestEngine, out_dir: Path, log) -> None:
    profiler = cProfile.Profile()
    profiler.enable()
    try:
        engine.run()
    finally:
        profiler.disable()
        prof_path = out_dir / "run.prof"
        profiler.dump_stats(str(prof_path))
        log.info(f"[profile] dumped to {prof_path}")
        log.info("[profile] top 20 by cumulative time:")
        pstats.Stats(profiler).sort_stats("cumulative").print_stats(20)


# ─────────────────────────────────────────────────────────────────────────
# Stats
# ─────────────────────────────────────────────────────────────────────────
def _register_statistics(engine: BacktestEngine) -> None:
    """Register pyo3-backed metrics on the engine's portfolio analyzer.

    Must be called before ``engine.run()`` so the analyzer attaches to the
    incoming position/return stream.
    """
    analyzer = engine.portfolio.analyzer
    for stat in (
        WinRate(), ProfitFactor(), Expectancy(), SharpeRatio(), SortinoRatio(),
        RiskReturnRatio(), ReturnsAverage(), ReturnsAverageWin(),
        ReturnsAverageLoss(), ReturnsVolatility(), LongRatio(), MaxWinner(),
        AvgWinner(), MinWinner(), MaxLoser(), AvgLoser(), MinLoser(),
    ):
        analyzer.register_statistic(stat)


def _bias_correctness_block(trades_log) -> list[str]:
    """For each bias bucket, measure whether the strategy's call paid out:
    direction-hit = favored leg (long for BULLISH, short for BEARISH) had
    positive PnL. Plus per-bucket session count and avg net session PnL so
    STRONG vs WEAK magnitude is visible.
    """
    if not trades_log:
        return []
    df = pd.DataFrame(trades_log)
    if df.empty or "bias" not in df.columns or "type" not in df.columns:
        return []

    df["is_bullish"] = df["bias"].str.contains("BULLISH", na=False)
    df["is_favored"] = (
        (df["is_bullish"] & (df["type"] == "long")) |
        (~df["is_bullish"] & (df["type"] == "short"))
    )
    favored = df[df["is_favored"]].copy()
    favored["hit"] = favored["pnl"] > 0
    session_pnl = df.groupby(["session_date", "bias"], as_index=False)["pnl"].sum()

    lines = []
    bull = favored[favored["is_bullish"]]
    bear = favored[~favored["is_bullish"]]
    if len(bull):
        lines.append(
            f"Bullish Direction Hit:          {bull['hit'].mean()*100:5.1f}%  "
            f"({int(bull['hit'].sum())} / {len(bull)})"
        )
    if len(bear):
        lines.append(
            f"Bearish Direction Hit:          {bear['hit'].mean()*100:5.1f}%  "
            f"({int(bear['hit'].sum())} / {len(bear)})"
        )

    order = ["STRONG_BULLISH", "WEAK_BULLISH", "WEAK_BEARISH", "STRONG_BEARISH"]
    for label in order:
        b_fav = favored[favored["bias"] == label]
        if b_fav.empty:
            continue
        b_sess = session_pnl[session_pnl["bias"] == label]
        hit = b_fav["hit"].mean() * 100
        net = b_sess["pnl"].mean()
        lines.append(
            f"{label}:".ljust(32)
            + f"N={len(b_sess):3d}  Hit={hit:5.1f}%  Net={net:>10,.0f}/sess"
        )

    # STRONG vs WEAK edge — does intensifying the label translate to PnL?
    strong = session_pnl[session_pnl["bias"].str.startswith("STRONG", na=False)]
    weak = session_pnl[session_pnl["bias"].str.startswith("WEAK", na=False)]
    if len(strong) and len(weak):
        lines.append(
            f"STRONG vs WEAK Avg Edge:        "
            f"{strong['pnl'].mean() - weak['pnl'].mean():>10,.0f}/sess  "
            f"(STRONG avg {strong['pnl'].mean():,.0f} vs WEAK {weak['pnl'].mean():,.0f})"
        )
    return lines


def _compute_and_write_stats(
    engine: BacktestEngine, strategy: "HedgeStrategy", instrument, out_dir: Path, log
) -> None:
    """Hydrate the analyzer with closed positions + account, then dump
    formatted stats to stdout and ``stats.txt``.
    """
    analyzer = engine.portfolio.analyzer
    account = engine.cache.account_for_venue(SIM_VENUE)
    positions = engine.cache.positions_closed()

    if account is None or not positions:
        log.warning("[stats] no account or closed positions — skipping analyzer")
        return

    analyzer.calculate_statistics(account, positions)

    quote = instrument.quote_currency
    fee_total = sum(
        c.as_double()
        for pos in positions
        for c in pos.commissions()
        if c.currency == quote
    )

    fees_block = [
        f"Total Fees:                     {fee_total:,.2f}",
        f"Avg Fee per Position:           {fee_total / len(positions):,.4f}",
    ]

    bias_block = _bias_correctness_block(getattr(strategy, "trades_log", None))

    sections = [
        ("General", analyzer.get_stats_general_formatted()),
        (f"PnLs ({quote.code})", analyzer.get_stats_pnls_formatted(quote)),
        (f"Fees ({quote.code})", fees_block),
        ("Returns", analyzer.get_stats_returns_formatted()),
    ]
    if bias_block:
        sections.insert(3, ("Bias Correctness", bias_block))

    lines = []
    for title, block in sections:
        lines.append(f"== {title} ==")
        lines.extend(block)
        lines.append("")

    text = "\n".join(lines)
    (out_dir / "stats.txt").write_text(text, encoding="utf-8")
    for line in lines:
        log.info(line)


# ─────────────────────────────────────────────────────────────────────────
# Results
# ─────────────────────────────────────────────────────────────────────────
def _persist_results(
    engine: BacktestEngine, strategy: HedgeStrategy, out_dir: Path, log
) -> None:
    try:
        engine.trader.generate_account_report(SIM_VENUE).to_csv(out_dir / "account.csv")
    except Exception as e:  # pragma: no cover — Nautilus quirks
        log.warning(f"account report failed: {e}")
    try:
        engine.trader.generate_order_fills_report().to_csv(out_dir / "fills.csv")
    except Exception as e:
        log.warning(f"fills report failed: {e}")
    try:
        engine.trader.generate_positions_report().to_csv(out_dir / "positions.csv")
    except Exception as e:
        log.warning(f"positions report failed: {e}")

    # Strategy's TVCharts-parity buffer (one entry per session entry).
    recorded = getattr(strategy, "recorded_data", None)
    if recorded:
        with open(out_dir / "recorded_data.pkl", "wb") as f:
            pickle.dump(recorded, f, protocol=pickle.HIGHEST_PROTOCOL)
        log.info(f"[results] {len(recorded)} recorded events pickled")

    # Per-position trade log — entry/exit + bias votes + indicator values.
    trades = getattr(strategy, "trades_log", None)
    if trades:
        cols = [
            "entry_date", "exit_date", "entry_price", "exit_price",
            "type", "size", "pnl", "return", "exit_reason",
            "session_date", "bias", "bullish_score", "bearish_score",
            "tie_broken", "adx_active",
            "vote_ema50", "vote_rsi", "vote_macd", "vote_pdh_pdl", "vote_vwap",
            "atr", "ema50", "rsi", "macd_hist", "adx", "di_pos", "di_neg",
            "prev_high", "prev_low", "prev_close", "ref_price", "vwap",
            "entry_close",
        ]
        df = (
            pd.DataFrame(trades)
            .reindex(columns=cols)
            .sort_values("entry_date")
            .reset_index(drop=True)
        )
        df.to_parquet(out_dir / "trades.parquet")
        df.to_csv(out_dir / "trades.csv", index=False)
        log.info(f"[results] {len(df)} positions written to trades.parquet")


# ─────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────
def main(args) -> None:
    out_dir = _setup_run_dir()
    log = _setup_python_logging(out_dir)

    log.info("=" * 60)
    log.info(f"Backtest: {TICKER} / {SESSION}")
    log.info(f"Range:    {STARTDATE} -> {ENDDATE}")
    log.info(f"Out dir:  {out_dir}")
    log.info("=" * 60)

    engine = _build_engine(out_dir)
    instrument = setup_forex_instrument(TICKER, venue=str(SIM_VENUE))
    _register_venue(engine, _build_fill_model(), instrument, log)
    _register_instrument_and_data(engine, instrument, log)
    strategy = _register_strategy(engine, instrument, log)
    _register_statistics(engine)

    log.info("[run] starting engine...")
    t0 = time.perf_counter()
    try:
        if args.profile:
            _run_with_profile(engine, out_dir, log)
        else:
            engine.run()
    finally:
        wall = time.perf_counter() - t0
        log.info(f"[run] finished in {wall:.1f}s ({wall/60:.1f} min)")
        _persist_results(engine, strategy, out_dir, log)
        _compute_and_write_stats(engine, strategy, instrument, out_dir, log)
        _dump_indicators_for_run(out_dir, log)
        engine.dispose()

    log.info(f"[done] results in {out_dir}")


def _dump_indicators_for_run(out_dir: Path, log) -> None:
    """Emit ``indicators.parquet`` so the tvcharts UI can render overlays.

    Imported lazily so the script's dependencies don't slow down `main` imports.
    """
    try:
        from scripts.dump_indicators import dump_indicators

        path = dump_indicators(out_dir.name)
        log.info(f"[indicators] dumped -> {path.relative_to(OUTPUT_DIR.parent)}")
    except Exception as e:  # noqa: BLE001
        log.warning(f"[indicators] dump failed: {type(e).__name__}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Single-ticker backtest runner. "
        "Ticker/session live in config.py — edit there, not here."
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Wrap engine.run() in cProfile and dump <out_dir>/run.prof",
    )
    main(parser.parse_args())
