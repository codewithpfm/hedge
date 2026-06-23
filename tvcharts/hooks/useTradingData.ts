//tvcharts/hooks/useTradingData.ts
import { useQuery } from "@tanstack/react-query";
import {
  fetchCandles,
  fetchIndicators,
  fetchRuns,
  fetchTrades,
  fetchStats,
} from "../fetchers";
import type { Timeframe } from "../fetchers";
import type { IndicatorName } from "../types/trading";

interface UseTradingDataParams {
  runId: string | null;
  tf: Timeframe;
  queryRange: { start: string | null; end: string | null };
  canFetchCandles: boolean;
  selectedIndicators: IndicatorName[];
}

export const useTradingData = ({
  runId,
  tf,
  queryRange,
  canFetchCandles,
  selectedIndicators,
}: UseTradingDataParams) => {
  const { data: runners } = useQuery({
    queryKey: ["runners"],
    queryFn: () => fetchRuns(),
  });

  const {
    data: stats,
    isLoading: statsLoading,
    error: statsError,
  } = useQuery({
    queryKey: ["stats", runId],
    queryFn: () => fetchStats(runId as string),
    enabled: runId !== null,
  });

  const {
    data: candles,
    isLoading: candlesLoading,
    error: candlesError,
  } = useQuery({
    queryKey: ["candles", runId, tf, queryRange.start, queryRange.end],
    queryFn: () =>
      fetchCandles(runId as string, tf, queryRange.start, queryRange.end),
    enabled: canFetchCandles,
  });

  // Two trade queries:
  //   1. ``trades`` is filtered to the visible chart window so on-chart
  //      markers stay performant when zoomed in.
  //   2. ``allTrades`` ignores the range so the sidebar can show every trade
  //      in the run (526 rows is fine to fetch once per run).
  const { data: trades } = useQuery({
    queryKey: ["trades", runId, queryRange.start, queryRange.end],
    queryFn: () =>
      fetchTrades(runId as string, queryRange.start, queryRange.end),
    enabled: canFetchCandles,
  });

  const { data: allTrades } = useQuery({
    queryKey: ["trades-all", runId],
    queryFn: () => fetchTrades(runId as string),
    enabled: runId !== null,
  });

  // Indicator series — query keyed on the sorted name list so toggling the
  // dropdown doesn't fetch unnecessary supersets. Cached per (run, range, set).
  const indicatorKey = [...selectedIndicators].sort().join(",");
  const { data: indicators } = useQuery({
    queryKey: [
      "indicators",
      runId,
      queryRange.start,
      queryRange.end,
      indicatorKey,
    ],
    queryFn: () =>
      fetchIndicators(
        runId as string,
        selectedIndicators,
        queryRange.start,
        queryRange.end
      ),
    enabled: canFetchCandles && selectedIndicators.length > 0,
  });

  return {
    runners,
    stats,
    statsLoading,
    statsError,
    candles,
    candlesLoading,
    candlesError,
    trades,
    allTrades,
    indicators,
  };
};
