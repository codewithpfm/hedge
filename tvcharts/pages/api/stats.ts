import type { NextApiRequest, NextApiResponse } from "next";
import {
  futuresCachePath,
  init,
  readRunMeta,
  runTradesPath,
} from "../../server/duck";
import { normalizeData } from "../../utils/data";

// Backtest runs no longer emit a dedicated ``stats.parquet`` — derive the same
// shape from ``trades.parquet`` so the existing chart UI keeps working without
// changing its data model.
//
// The chart's date-range picker is driven by ``start_date``/``end_date``.
// Returning the raw trades range would let the user pick a window where the
// cached candles parquet has no data (the cache is often narrower than the
// backtest span), so we return the intersection of "trades have entries" and
// "candles exist in cache" — guarantees the default 1M view lands somewhere
// renderable.
const getStatsForRun = async (req: NextApiRequest, res: NextApiResponse) => {
  try {
    const { runId } = req.query;
    if (typeof runId !== "string") {
      res.status(400).json({ error: "Please provide a valid runId" });
      return;
    }

    const meta = readRunMeta(runId);
    if (!meta) {
      res.status(404).json({ error: `Run not found: ${runId}` });
      return;
    }

    const db = await init();
    const tradesFile = runTradesPath(runId).replace(/\\/g, "/");
    const candlesFile = futuresCachePath(meta.ticker).replace(/\\/g, "/");

    const rows = await db.all(`
      WITH t AS (
        SELECT
          COUNT(*)::BIGINT                                  AS total_trades,
          COALESCE(SUM(pnl), 0)                             AS total_pnl,
          COALESCE(AVG(CASE WHEN pnl > 0 THEN 1.0 ELSE 0.0 END), 0) AS win_rate,
          MIN(entry_date)                                   AS t_min,
          MAX(exit_date)                                    AS t_max
        FROM read_parquet('${tradesFile}')
      ),
      c AS (
        SELECT MIN(Datetime) AS c_min, MAX(Datetime) AS c_max
        FROM read_parquet('${candlesFile}')
      )
      SELECT
        t.total_trades,
        t.total_pnl,
        t.win_rate,
        GREATEST(t.t_min, c.c_min) AS start_date,
        LEAST(t.t_max,    c.c_max) AS end_date
      FROM t, c
    `);

    const row = rows[0] ?? {};
    res.status(200).json(
      normalizeData([
        {
          total_trades: Number(row.total_trades ?? 0),
          total_pnl: Number(row.total_pnl ?? 0),
          win_rate: Number(row.win_rate ?? 0),
          start_date: row.start_date ?? meta.start,
          end_date: row.end_date ?? meta.end,
        },
      ])
    );
  } catch (err: any) {
    console.error("API Error in /api/stats:", err);
    res.status(500).json({ error: err?.message || "Internal server error" });
  }
};

export default getStatsForRun;
