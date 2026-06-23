//tvcharts/fetchers/indicators.ts
import axios from "axios";
import type { IndicatorName, IndicatorRow } from "../types/trading";

export async function fetchIndicators(
  runId: string,
  names: IndicatorName[],
  start?: string | null,
  end?: string | null
): Promise<IndicatorRow[]> {
  if (names.length === 0) return [];
  const params: Record<string, any> = {
    runId,
    names: names.join(","),
  };
  if (start && end) {
    params.start = `${start} 00:00:00`;
    params.end = `${end} 23:59:59`;
  }
  const response = await axios.get("/api/indicators", { params });
  return response.data;
}
