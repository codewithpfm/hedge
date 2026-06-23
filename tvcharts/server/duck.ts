// tvcharts/server/duck.ts

import { Database } from "duckdb-async";
import * as path from "path";
import * as fs from "fs";

// All paths are resolved from the tvcharts working directory (where `next dev`
// runs). The runs folder holds per-backtest artefacts; the futures folder is
// the shared Polygon parquet cache that backs every chart's price data.
const RUNS_DIR = path.resolve(process.cwd(), "..", "runs");
const FUTURES_DIR = path.resolve(process.cwd(), "..", ".futures");

let dbInstance: Database | null = null;
let isInitializing = false;
let initQueue: Array<(db: Database) => void> = [];

// In-memory DuckDB — we only query external parquet files, so there is no
// state to persist. Using an on-disk database would cause file-lock conflicts
// under Next.js HMR (a stale handle from the previous worker prevents the new
// one from opening the same .db file).
export const init = async (): Promise<Database> => {
  if (dbInstance) return dbInstance;

  if (isInitializing) {
    return new Promise((resolve) => {
      initQueue.push(resolve);
    });
  }

  isInitializing = true;
  try {
    dbInstance = await Database.create(":memory:");
    initQueue.forEach((resolve) => resolve(dbInstance!));
    initQueue = [];
    return dbInstance;
  } catch (error) {
    console.error("Failed to initialize DuckDB:", error);
    initQueue = [];
    throw new Error(`Database initialization failed: ${error}`);
  } finally {
    isInitializing = false;
  }
};

// ─────────────────────────────────────────────────────────────────────────
// Paths
// ─────────────────────────────────────────────────────────────────────────
export const runDir = (runId: string) => path.join(RUNS_DIR, runId);
export const runMetaPath = (runId: string) => path.join(runDir(runId), "run_meta.json");
export const runTradesPath = (runId: string) => path.join(runDir(runId), "trades.parquet");
export const runIndicatorsPath = (runId: string) =>
  path.join(runDir(runId), "indicators.parquet");

// Polygon currency tickers are cached on disk with ``:`` replaced by ``_`` —
// see storelib/handlers/parquet.py::_safe_filename.
export const futuresCachePath = (ticker: string) =>
  path.join(FUTURES_DIR, `C_${ticker}.parquet`);

// ─────────────────────────────────────────────────────────────────────────
// Run metadata
// ─────────────────────────────────────────────────────────────────────────
export interface RunMeta {
  id: string;
  ticker: string;
  session: string;
  start: string;
  end: string;
  created_at: string;
  starting_balance_usd?: number;
  leverage?: number;
  risk_percent?: number;
}

export const readRunMeta = (runId: string): RunMeta | null => {
  const p = runMetaPath(runId);
  if (!fs.existsSync(p)) return null;
  try {
    const meta = JSON.parse(fs.readFileSync(p, "utf-8"));
    return { id: runId, ...meta };
  } catch (e) {
    console.error(`Failed to read run meta for ${runId}:`, e);
    return null;
  }
};

export const listRuns = (): RunMeta[] => {
  if (!fs.existsSync(RUNS_DIR)) return [];
  return fs
    .readdirSync(RUNS_DIR, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => readRunMeta(d.name))
    .filter((r): r is RunMeta => r !== null)
    // Only surface runs the chart can actually render — must have both a
    // trades.parquet and a cached candles parquet for the run's ticker.
    .filter(
      (r) =>
        fs.existsSync(runTradesPath(r.id)) &&
        fs.existsSync(futuresCachePath(r.ticker))
    )
    .sort((a, b) => a.created_at.localeCompare(b.created_at));
};

// ─────────────────────────────────────────────────────────────────────────
// Candle resampling
// ─────────────────────────────────────────────────────────────────────────
// Whitelist what callers can ask for so a stray ``tf`` value can't open a SQL
// injection path through ``time_bucket``.
export const TIMEFRAME_TO_INTERVAL: Record<string, string> = {
  "1m": "1 minute",
  "5m": "5 minutes",
  "15m": "15 minutes",
  "30m": "30 minutes",
  "1h": "1 hour",
  "4h": "4 hours",
  "1d": "1 day",
};

export interface ResampleOpts {
  ticker: string;
  tf: string;
  start?: string | null;
  end?: string | null;
}

export const resampleCandles = async ({ ticker, tf, start, end }: ResampleOpts) => {
  const interval = TIMEFRAME_TO_INTERVAL[tf];
  if (!interval) {
    throw new Error(`Invalid timeframe: ${tf}. Expected one of ${Object.keys(TIMEFRAME_TO_INTERVAL).join(", ")}`);
  }

  const file = futuresCachePath(ticker);
  if (!fs.existsSync(file)) {
    throw new Error(`No cached candles for ${ticker} at ${file}`);
  }

  const db = await init();
  const filePath = file.replace(/\\/g, "/");
  const where: string[] = [];
  if (start) where.push(`Datetime >= TIMESTAMPTZ '${start}'`);
  if (end) where.push(`Datetime <= TIMESTAMPTZ '${end}'`);
  const whereSql = where.length ? `WHERE ${where.join(" AND ")}` : "";

  const QUERY = `
    SELECT
      time_bucket(INTERVAL '${interval}', Datetime) AS Datetime,
      first(Open  ORDER BY Datetime) AS Open,
      max(High)                       AS High,
      min(Low)                        AS Low,
      last(Close ORDER BY Datetime)  AS Close,
      sum(Volume)                     AS Volume
    FROM read_parquet('${filePath}')
    ${whereSql}
    GROUP BY 1
    ORDER BY 1;
  `;
  return await db.all(QUERY);
};

// ─────────────────────────────────────────────────────────────────────────
// Generic parquet reader (used by trades and stats endpoints)
// ─────────────────────────────────────────────────────────────────────────
export const readParquet = async (absPath: string, whereSql: string = "") => {
  if (!fs.existsSync(absPath)) {
    throw new Error(`Parquet not found: ${absPath}`);
  }
  const db = await init();
  const QUERY = `SELECT * FROM read_parquet('${absPath.replace(/\\/g, "/")}') ${whereSql}`;
  return await db.all(QUERY);
};
