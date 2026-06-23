import type { NextApiRequest, NextApiResponse } from "next";
import * as fs from "fs";
import {
  init,
  readRunMeta,
  runIndicatorsPath,
} from "../../server/duck";
import { normalizeData } from "../../utils/data";

// Per-run indicator series live in runs/{id}/indicators.parquet, produced by
// scripts/dump_indicators.py — it runs the strategy's own indicator classes
// over the run's candles so the chart shows exactly what the strategy saw.
//
// If a run hasn't been dumped yet (older runs predate the script), we return
// an empty array so the chart degrades gracefully instead of 500-ing.

const ALLOWED_NAMES = new Set([
  "ema50", "vwap",
  "prev_high", "prev_low", "prev_close",
  "atr", "rsi", "adx", "di_pos", "di_neg",
  "macd_value", "macd_signal", "macd_hist",
]);

const getIndicatorsForRun = async (
  req: NextApiRequest,
  res: NextApiResponse
) => {
  try {
    const { runId, start, end, names } = req.query;

    if (typeof runId !== "string") {
      res.status(400).json({ error: "Please provide a valid runId" });
      return;
    }
    if (!readRunMeta(runId)) {
      res.status(404).json({ error: `Run not found: ${runId}` });
      return;
    }

    const file = runIndicatorsPath(runId);
    if (!fs.existsSync(file)) {
      res.status(200).json([]);
      return;
    }

    // Optional comma-separated column filter — silently drops unknown names so
    // a typo can't surface SQL errors to the client.
    let projection = "*";
    if (typeof names === "string" && names.length > 0) {
      const cols = names
        .split(",")
        .map((s) => s.trim())
        .filter((s) => ALLOWED_NAMES.has(s));
      if (cols.length > 0) {
        projection = ["Datetime", ...cols].join(", ");
      }
    }

    const where: string[] = [];
    if (typeof start === "string") where.push(`Datetime >= TIMESTAMPTZ '${start}'`);
    if (typeof end === "string") where.push(`Datetime <= TIMESTAMPTZ '${end}'`);
    const whereSql = where.length ? `WHERE ${where.join(" AND ")}` : "";

    const db = await init();
    const filePath = file.replace(/\\/g, "/");
    const rows = await db.all(
      `SELECT ${projection} FROM read_parquet('${filePath}') ${whereSql} ORDER BY Datetime`
    );
    res.status(200).json(normalizeData(rows));
  } catch (err: any) {
    console.error("API Error in /api/indicators:", err);
    res
      .status(500)
      .json({ error: err?.message || "Internal server error" });
  }
};

export default getIndicatorsForRun;
