import type { NextApiRequest, NextApiResponse } from "next";
import { readRunMeta } from "../../server/duck";

// The run config now lives in run_meta.json (ticker, session, start, end,
// risk_percent, leverage, …). Surface it directly so the UI doesn't have to
// know about a separate params.parquet that no longer exists.
const getParamsForRun = async (req: NextApiRequest, res: NextApiResponse) => {
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

  res.status(200).json([meta]);
};

export default getParamsForRun;
