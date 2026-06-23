//fetchers/stats.ts
import axios from "axios";

export async function fetchStats(runId: string) {
  const response = await axios.get(`/api/stats?runId=${runId}`);
  return response.data;
}
