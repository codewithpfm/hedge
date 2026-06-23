"""Compute per-run indicators and dump them to ``runs/{id}/indicators.parquet``.

The chart UI loads this parquet to render indicator overlays. Values are
produced by the same indicator classes the strategy uses
(``strategy.indicators.DailyIndicators`` and ``SessionVWAP``), so what the
chart shows is exactly what the strategy saw at decision time.

Usage::

    python scripts/dump_indicators.py --run-id USDJPY_london_20260525_192837
    python scripts/dump_indicators.py --all
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

# Allow ``python scripts/dump_indicators.py`` to import the project's modules
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from nautilus_trader.model.data import Bar, BarType  # noqa: E402
from nautilus_trader.persistence.wranglers import BarDataWrangler  # noqa: E402

from strategy.indicators import DailyIndicators, SessionVWAP  # noqa: E402
from utils.maps import session_open_hour  # noqa: E402
from utils.nautilus_converter import setup_forex_instrument  # noqa: E402

WARMUP_DAYS = 60  # match main.py — Wilder ATR/EMA need a long bootstrap
SIM_VENUE = "SIM"


# ─────────────────────────────────────────────────────────────────────────
# Resampling — mirrors the strategy's inline aggregation in
# hedge_strategy.py:_aggregate_daily / _aggregate_vwap
# ─────────────────────────────────────────────────────────────────────────
def _resample_ohlcv(df_1m: pd.DataFrame, rule: str) -> pd.DataFrame:
    """1M -> arbitrary OHLCV bars, dropping incomplete buckets."""
    df = df_1m.rename(columns=str.lower)
    keep = ["open", "high", "low", "close"]
    if "volume" in df.columns:
        keep.append("volume")
    df = df[keep]
    out = (
        df.resample(rule, label="left", closed="left")
        .agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                **({"volume": "sum"} if "volume" in df.columns else {}),
            }
        )
        .dropna()
    )
    return out


def _to_bars(df: pd.DataFrame, instrument, bar_type_str: str) -> list[Bar]:
    """Wrap a resampled OHLCV DataFrame into Nautilus ``Bar`` objects via the
    same wrangler the backtest uses (``main.py:_wrangle_bars``) so the
    indicators warm up on byte-identical inputs."""
    bar_type = BarType.from_str(bar_type_str)
    wrangler = BarDataWrangler(bar_type=bar_type, instrument=instrument)
    return wrangler.process(df)


# ─────────────────────────────────────────────────────────────────────────
# Indicator simulation
# ─────────────────────────────────────────────────────────────────────────
def _daily_snapshots(daily_bars: list[Bar]) -> pd.DataFrame:
    """Feed daily bars to ``DailyIndicators`` and capture the snapshot after
    each one. The snapshot for a bar dated D becomes the value the strategy
    sees during *the following* session — encoded by ``visible_from``.
    """
    di = DailyIndicators()
    rows = []
    for bar in daily_bars:
        di.handle_bar(bar)
        if not di.initialized:
            # ATR/EMA/etc haven't warmed up yet — record NaNs so the chart
            # leaves a gap rather than a misleading flat line.
            day = datetime.fromtimestamp(bar.ts_event / 1e9, tz=timezone.utc).date()
            rows.append({"date": day, **{k: None for k in _DAILY_COLS}})
            continue
        snap = di.snapshot()
        day = datetime.fromtimestamp(bar.ts_event / 1e9, tz=timezone.utc).date()
        rows.append({
            "date": day,
            "ema50": snap["ema50"],
            "atr": snap["atr"],
            "rsi": snap["rsi"],
            "adx": snap["adx"],
            "di_pos": snap["di_pos"],
            "di_neg": snap["di_neg"],
            "macd_value": snap["macd"],
            "macd_signal": snap["macd_signal"],
            "macd_hist": snap["macd_hist"],
            "prev_high": snap["prev_high"],
            "prev_low": snap["prev_low"],
            "prev_close": snap["prev_close"],
        })
    df = pd.DataFrame(rows).set_index("date")
    return df


_DAILY_COLS = [
    "ema50", "atr", "rsi", "adx", "di_pos", "di_neg",
    "macd_value", "macd_signal", "macd_hist",
    "prev_high", "prev_low", "prev_close",
]


def _vwap_snapshots(vwap_bars: list[Bar], session: str) -> pd.DataFrame:
    """Feed 30M bars to ``SessionVWAP`` and capture ``.effective`` after each."""
    vw = SessionVWAP(session)
    rows = []
    for bar in vwap_bars:
        vw.handle_bar(bar)
        ts = pd.Timestamp(bar.ts_event, unit="ns", tz="UTC")
        rows.append({"Datetime": ts, "vwap": vw.effective})
    return pd.DataFrame(rows).set_index("Datetime")


# ─────────────────────────────────────────────────────────────────────────
# Per-run driver
# ─────────────────────────────────────────────────────────────────────────
def _candles_path(ticker: str) -> Path:
    # See storelib/handlers/parquet.py::_safe_filename — ``:`` was sanitized to
    # ``_`` on disk so the cache works on Windows.
    return _REPO_ROOT / ".futures" / f"C_{ticker}.parquet"


def dump_indicators(run_id: str) -> Path:
    run_dir = _REPO_ROOT / "runs" / run_id
    meta_path = run_dir / "run_meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"No run_meta.json at {meta_path}")

    meta = json.loads(meta_path.read_text())
    ticker = meta["ticker"]
    session = meta["session"]

    candles_file = _candles_path(ticker)
    if not candles_file.exists():
        raise FileNotFoundError(
            f"No cached candles for {ticker} at {candles_file}. "
            f"Prime the cache via Fetcher(dir='futures').get('C:{ticker}', ...)"
        )

    # Load 1M bars, trim to [start - warmup, end] to bootstrap the daily stack
    df = pd.read_parquet(candles_file)
    df = df.dropna()
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, utc=True)
    df.index = df.index.tz_convert("UTC")

    start = pd.Timestamp(meta["start"], tz="UTC") - pd.Timedelta(days=WARMUP_DAYS)
    end = pd.Timestamp(meta["end"], tz="UTC") + pd.Timedelta(days=1)
    df = df.loc[(df.index >= start) & (df.index <= end)]
    if df.empty:
        raise RuntimeError(
            f"Cache for {ticker} has no rows in [{start}, {end}]. "
            f"Extend the Polygon cache and retry."
        )

    instrument = setup_forex_instrument(ticker, venue=SIM_VENUE)

    # Build daily bars and feed DailyIndicators
    daily_df = _resample_ohlcv(df, "1D")
    daily_df.index.name = "Datetime"
    daily_bars = _to_bars(
        daily_df, instrument, f"{instrument.id}-1-DAY-LAST-EXTERNAL"
    )
    daily_snap = _daily_snapshots(daily_bars)

    # Build 30M bars and feed SessionVWAP
    vwap_df = _resample_ohlcv(df, "30min")
    vwap_df.index.name = "Datetime"
    vwap_bars = _to_bars(
        vwap_df, instrument, f"{instrument.id}-30-MINUTE-LAST-EXTERNAL"
    )
    vwap_snap = _vwap_snapshots(vwap_bars, session)

    # Join — for each 30M timestamp, attach the daily snapshot from the
    # *previous* UTC calendar day (matches how the strategy reads the daily
    # stack: a Feb-18 bar sees Feb-17's daily values).
    out = vwap_snap.copy()
    out["_prev_date"] = (out.index - pd.Timedelta(days=1)).date
    out["_prev_date"] = pd.to_datetime(out["_prev_date"])
    daily_lookup = daily_snap.copy()
    daily_lookup.index = pd.to_datetime(daily_lookup.index)
    out = out.join(daily_lookup, on="_prev_date").drop(columns=["_prev_date"])

    # Trim back to the run's actual window (drop warmup tail)
    out = out.loc[out.index >= pd.Timestamp(meta["start"], tz="UTC")]
    out = out.reset_index()
    out["Datetime"] = pd.to_datetime(out["Datetime"], utc=True)

    out_path = run_dir / "indicators.parquet"
    out.to_parquet(out_path, index=False)
    return out_path


def _list_all_run_ids() -> list[str]:
    runs_dir = _REPO_ROOT / "runs"
    if not runs_dir.exists():
        return []
    return sorted(
        d.name for d in runs_dir.iterdir()
        if d.is_dir() and (d / "run_meta.json").exists()
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--run-id", help="Specific run directory name to dump")
    g.add_argument("--all", action="store_true", help="Dump every run under runs/")
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip runs that already have indicators.parquet (only with --all)",
    )
    args = parser.parse_args()

    ids = [args.run_id] if args.run_id else _list_all_run_ids()
    n_ok = n_skip = n_err = 0
    for rid in ids:
        out = _REPO_ROOT / "runs" / rid / "indicators.parquet"
        if args.skip_existing and out.exists():
            print(f"[skip ] {rid}  (exists)")
            n_skip += 1
            continue
        try:
            path = dump_indicators(rid)
            n_ok += 1
            print(f"[ ok  ] {rid} -> {path.relative_to(_REPO_ROOT)}")
        except FileNotFoundError as e:
            n_skip += 1
            print(f"[skip ] {rid}  ({e})")
        except Exception as e:  # noqa: BLE001
            n_err += 1
            print(f"[ERR  ] {rid}  {type(e).__name__}: {e}")

    print(f"\nDone. ok={n_ok}  skip={n_skip}  err={n_err}")


if __name__ == "__main__":
    main()
