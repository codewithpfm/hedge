import axios from "axios";

export type Timeframe = "1m" | "5m" | "15m" | "30m" | "1h" | "4h" | "1d";

export const TIMEFRAMES: Timeframe[] = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"];

export interface Candle {
  Datetime: string;
  Open: number;
  High: number;
  Low: number;
  Close: number;
  Volume?: number;
}

export async function fetchCandles(
  runId: string,
  tf: Timeframe,
  startDate?: string | null,
  endDate?: string | null
): Promise<Candle[]> {
  try {
    const params: Record<string, any> = { runId, tf };
    if (startDate && endDate) {
      params.start = `${startDate} 00:00:00`;
      params.end = `${endDate} 23:59:59`;
    }
    const response = await axios.get("/api/candles", { params });
    return response.data;
  } catch (error: any) {
    console.error("Failed to fetch candles:", error);
    throw new Error(
      error.response?.data?.error || "Failed to fetch candles from server"
    );
  }
}
