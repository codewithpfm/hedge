import type { NextApiRequest, NextApiResponse } from "next";
import { listRuns } from "../../server/duck";

const getRunner = async (_req: NextApiRequest, res: NextApiResponse) => {
  try {
    const runs = listRuns();
    res.status(200).json({
      total: runs.length,
      latest: runs[runs.length - 1] ?? null,
      runs,
    });
  } catch (err: any) {
    console.error("API Error in /api/runs:", err);
    res.status(500).json({ error: err?.message || "Internal server error" });
  }
};

export default getRunner;
