import type { NextApiRequest, NextApiResponse } from "next";
import { readParquet, readRunMeta, runTradesPath } from "../../server/duck";
import { normalizeData } from "../../utils/data";

const getTradesForRun = async (req: NextApiRequest, res: NextApiResponse) => {
  try {
    const { runId, start, end } = req.query;
    if (typeof runId !== "string") {
      res.status(400).json({ error: "Please provide a valid runId" });
      return;
    }

    if (!readRunMeta(runId)) {
      res.status(404).json({ error: `Run not found: ${runId}` });
      return;
    }

    const where: string[] = [];
    if (typeof start === "string") where.push(`entry_date >= TIMESTAMPTZ '${start}'`);
    if (typeof end === "string") where.push(`entry_date <= TIMESTAMPTZ '${end}'`);
    const whereSql = where.length ? `WHERE ${where.join(" AND ")}` : "";

    const trades = await readParquet(runTradesPath(runId), whereSql);
    res.status(200).json(normalizeData(trades));
  } catch (err: any) {
    console.error("API Error in /api/trades:", err);
    res.status(500).json({ error: err?.message || "Internal server error" });
  }
};

export default getTradesForRun;
