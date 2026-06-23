//tvcharts/fetchers/trades.ts
import axios from "axios";

export async function fetchTrades(
  runId: string,
  start?: string | null,
  end?: string | null
) {
  let url = `/api/trades?runId=${runId}`;
  if (start && end) {
    url += `&start=${start} 00:00:00&end=${end} 23:59:59`;
  }
  const response = await axios.get(url);
  return response.data;
}
