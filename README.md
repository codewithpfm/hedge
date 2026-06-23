# 💹 Nautilus-Powered Forex Trading System

An institutional-grade algorithmic trading system for USD/JPY, unified under the **NautilusTrader** framework. This system replaces the previous fragmented Lumibot and custom execution models with a single, high-performance, event-driven architecture.

## 🚀 Key Features

- **Unified Logic**: The exact same strategy code runs in both backtesting and live trading.
- **Event-Driven**: Built on NautilusTrader (Rust/Cython) for sub-millisecond execution and robust order management.
- **MetaTrader 5 Native**: Direct connectivity to MT5 for live execution and historical data ingestion.
- **Multi-Timeframe Analysis**: Precise 1M execution with 8M signal generation and 4H trend filtering.
- **Dynamic Training**: Monthly rolling window for threshold and risk parameter optimization.

## 🏗️ System Architecture

The system is composed of four horizontal layers — **Data**, **Strategy**, **Execution**, and **Analytics/UI** — wired together by the NautilusTrader event bus. The same `HedgeStrategy` class is instantiated by either the `BacktestEngine` (offline) or the `LiveNode` (online), guaranteeing behavioural parity between simulation and production.

### High-Level Diagram

```
                       ┌──────────────────────────────────────────────────────┐
                       │                    CONFIGURATION                     │
                       │  config.py  ·  utils/instrument_specs.py  ·  .env    │
                       │  (TICKER, SESSION, RISK_PERCENT, ATR thresholds…)    │
                       └──────────────────────────────────────────────────────┘
                                              │
                ┌─────────────────────────────┼─────────────────────────────┐
                ▼                             ▼                             ▼
   ┌─────────────────────┐       ┌─────────────────────────┐    ┌──────────────────────┐
   │      DATA LAYER     │       │     STRATEGY LAYER      │    │   EXECUTION LAYER    │
   │  storelib/          │       │  strategy/              │    │  nautilus_mt5/       │
   │   ├─ fetcher.py     │       │   ├─ hedge_strategy.py  │    │   ├─ data_client.py  │
   │   ├─ urls.py        │──────▶│   ├─ bias_engine.py     │───▶│   └─ exec_client.py  │
   │   ├─ mt5_source.py  │ Bars  │   └─ indicators.py      │    │                      │
   │   └─ handlers/      │       │                         │Order│  magic/connector.py  │
   │     parquet.py      │       │  utils/                 │ s   │  (MT5 broker layer)  │
   │                     │       │   ├─ maps.py (sessions) │    │                      │
   │  .futures/ cache    │       │   ├─ nautilus_converter │    │  MetaTrader 5 ◀──────┤
   └─────────────────────┘       │   └─ resampler.py       │    └──────────────────────┘
            ▲                    └─────────────────────────┘                │
            │                                │                              │
            │                                ▼                              ▼
   ┌──────────────────┐          ┌────────────────────────┐    ┌──────────────────────┐
   │   DATA SOURCES   │          │  NAUTILUS EVENT BUS    │    │     LIVE BROKER      │
   │  ┌────────────┐  │          │  (Rust / Cython core)  │    │  MT5 Terminal +      │
   │  │ Polygon.io │  │          │   ┌──────────────────┐ │    │  Pepperstone / OANDA │
   │  └────────────┘  │          │   │ BacktestEngine   │ │    │  (HEDGING account)   │
   │  ┌────────────┐  │          │   │   (main.py)      │ │    └──────────────────────┘
   │  │   MT5 hist │  │          │   └──────────────────┘ │
   │  └────────────┘  │          │   ┌──────────────────┐ │
   └──────────────────┘          │   │   LiveNode       │ │
                                 │   │   (live.py)      │ │
                                 │   └──────────────────┘ │
                                 └────────────────────────┘
                                              │
                                              ▼
                       ┌──────────────────────────────────────────────────────┐
                       │                  ANALYTICS / UI LAYER                │
                       │  runs/{TICKER_SESSION_TIMESTAMP}/                    │
                       │   ├─ trades.parquet  (entry/exit + bias votes)       │
                       │   ├─ stats.txt       (PnL, Sharpe, bias correctness) │
                       │   ├─ recorded_data.pkl  ·  run.prof  ·  *.csv        │
                       │   └─ indicators.parquet (from scripts/dump_indicators)│
                       │                                                      │
                       │  tvcharts/  (Next.js + TradingView Lightweight)      │
                       │   ├─ server/duck.ts   (in-memory DuckDB resampling)  │
                       │   ├─ pages/api/       (runs, candles, trades, stats) │
                       │   └─ components/      (chart, sidebar, trade modal)  │
                       └──────────────────────────────────────────────────────┘
```

### 1. Data Layer (`storelib/`)
Provider-agnostic market-data ingestion with parquet caching.
- **`fetcher.py`** — Unified `Fetcher.get()` API; routes Polygon-covered tickers (FX majors, USOIL) to `urls.py` and falls back to `mt5_source.py` for instruments outside Polygon's coverage (e.g. `XAUUSD`).
- **`handlers/parquet.py`** — Local cache under `.futures/`. Sanitises Polygon's `C:`/`X:` prefixes for Windows NTFS compatibility.
- **Warm-up padding** — `main.py` pads `STARTDATE` by `WARMUP_DAYS=60` so Wilder ATR / EMA50 bootstrap before the live test window.

### 2. Strategy Layer (`strategy/`)
The **single source of truth** for trading logic, shared by backtest and live paths.
- **`hedge_strategy.py` — `HedgeStrategy`**: subclass of Nautilus `Strategy`. On each 1-minute bar it aggregates 30-min VWAP and daily bars, detects session rollover, computes the daily bias, and opens a **dual position** (long + short) at session-open + delay. Per-leg SL/TP/max-hold monitor runs every bar — there is no session-close flatten.
- **`bias_engine.py` — `BiasEngine`**: five-voter ensemble (EMA50, RSI, MACD histogram, prior-day H/L, session VWAP) with an ADX-gated booster. Emits a 5-level `BiasLabel` (`STRONG_BULLISH` → `STRONG_BEARISH`) that maps to per-leg ATR-multiple SL/TP tables.
- **`indicators.py`**: `DailyIndicators` (EMA50, RSI, MACD, ATR, DI±/ADX) and `SessionVWAP` with previous-session carry-over.

### 3. Execution Layer (`nautilus_mt5/`)
Custom Nautilus adapters bridging the framework to MetaTrader 5.
- **`data_client.py` — `MT5DataClient`**: subclasses `LiveDataClient`; polls `mt5.symbol_info_tick()` asynchronously and emits `QuoteTick` events into the data engine.
- **`exec_client.py` — `MT5ExecutionClient`**: translates Nautilus order events into native MT5 trade tickets (magic-number tagged).
- **`magic/connector.py`** — thin broker wrapper handling MT5 login, server timezone, and account state.

### 4. Execution Nodes
- **Backtesting (`main.py`)**: builds a `BacktestEngine` with `OmsType.HEDGING` + `FixedFeeModel`, seeds the venue in the instrument's quote currency, wrangles cached bars via `BarDataWrangler`, registers `pyo3` portfolio statistics (Sharpe, Sortino, ProfitFactor, WinRate…), and emits a complete per-run artifact bundle.
- **Live trading (`live.py`)**: instantiates a Nautilus `LiveNode`, attaches the MT5 data/exec clients, and runs the **identical** `HedgeStrategy` instance forever.

### 5. Analytics & Visualization
- **Per-run output bundle** (`runs/{ticker_session_timestamp}/`): `trades.parquet` (one row per leg, with all 5 bias votes + indicator values), `stats.txt` (Nautilus `PortfolioAnalyzer` + custom **Bias Correctness** block measuring directional skill independent of trend), `account.csv`, `fills.csv`, `positions.csv`, `recorded_data.pkl`, optional `run.prof` (cProfile).
- **`tvcharts/`** — Next.js + TypeScript review UI. In-memory DuckDB resamples cached parquets via `time_bucket()`; API routes (`/api/runs`, `/api/candles`, `/api/trades`, `/api/stats`, `/api/indicators`) feed a TradingView Lightweight Charts canvas with overlay indicators (EMA50/VWAP/Prev H-L-C), ATR/ADX subplots, click-to-navigate trade markers, and a bias-snapshot detail modal.
- **`scripts/dump_indicators.py`** — replays the strategy's indicator classes over a run's candles to emit `indicators.parquet` for the UI, guaranteeing on-chart parity with what the live strategy saw.

### Design Invariants
1. **Backtest/live parity** — any change to entry/exit/sizing logic lives in `strategy/` so both `main.py` and `live.py` inherit it automatically.
2. **Hedging account required** — long and short legs must coexist; the venue is registered with `OmsType.HEDGING`.
3. **Per-symbol risk specs** — pip size, pip value, contract size, and min-lot live in `utils/instrument_specs.py`; adding a new tradeable instrument is a one-row change.
4. **Reproducible runs** — every backtest is a self-contained directory under `runs/` (config snapshot, trades, stats, profile, logs) that can be replayed in the UI without re-running the engine.

## 🚦 Getting Started

### Prerequisites
- Python 3.12+
- `uv` package manager
- MetaTrader 5 (for live trading or data fetching)

### Local Development
1. Clone the repository.
2. Install dependencies:
   ```bash
   uv sync
   ```
3. Set up your `.env` file with `POLYGON_API_KEY` (if fetching from Polygon) or configure MT5 credentials.

### Running a Backtest
```bash
uv run main.py
```
This will:
1. Fetch/Prepare high-frequency data.
2. Run the rolling monthly trainer and signal generator.
3. Convert data to Nautilus format.
4. Execute the backtest and save performance statistics.

### Running Live Trading
```bash
uv run magic_run.py
```
*(Requires MT5 terminal to be open and logged in)*

## 📈 Performance
Performance reports and QuantStats tearsheets are automatically generated and saved to the `logs/` directory after each backtest run.
