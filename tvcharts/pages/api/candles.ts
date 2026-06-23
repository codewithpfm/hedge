import type { NextApiRequest, NextApiResponse } from "next";
import {
  readRunMeta,
  resampleCandles,
  TIMEFRAME_TO_INTERVAL,
} from "../../server/duck";
import { normalizeData } from "../../utils/data";

export default async function getCandlesForRun(
  req: NextApiRequest,
  res: NextApiResponse
) {
  try {
    const { runId, tf, start, end } = req.query;

    if (typeof runId !== "string") {
      res.status(400).json({ error: "Please provide a valid runId" });
      return;
    }

    const meta = readRunMeta(runId);
    if (!meta) {
      res.status(404).json({ error: `Run not found: ${runId}` });
      return;
    }

    const timeframe = typeof tf === "string" ? tf : "1m";
    if (!(timeframe in TIMEFRAME_TO_INTERVAL)) {
      res.status(400).json({
        error: `Invalid tf: ${timeframe}`,
        allowed: Object.keys(TIMEFRAME_TO_INTERVAL),
      });
      return;
    }

    const candles = await resampleCandles({
      ticker: meta.ticker,
      tf: timeframe,
      start: typeof start === "string" ? start : null,
      end: typeof end === "string" ? end : null,
    });

    res.status(200).json(normalizeData(candles));
  } catch (err: any) {
    console.error("API Error in /api/candles:", err);
    res.status(500).json({
      error: err?.message || "Internal server error",
      details: process.env.NODE_ENV === "development" ? err?.stack : undefined,
    });
  }
}
