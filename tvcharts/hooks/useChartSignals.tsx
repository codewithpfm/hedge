//tvcharts/hooks/useChartSignals.tsx
import { useEffect } from "react";
import type { ISeriesApi } from "lightweight-charts";
import { bullColor, bearColor } from "./useLoadCandles";

type ChartSignalsProps = {
  candleSeries: ISeriesApi<"Candlestick"> | null;
  indicators: any[];
  showMarkers: boolean;
};

export const useChartSignals = ({ candleSeries, indicators, showMarkers }: ChartSignalsProps) => {
  useEffect(() => {
    if (!candleSeries) return;
    
    // If showMarkers is false, clear all markers
    if (!showMarkers) {
      candleSeries.setMarkers([]);
      console.log("🚫 Cleared signal markers from chart");
      return;
    }
    
    if (!indicators?.length) return;

    const longSignals = [];
    const shortSignals = [];

    for (const bar of indicators) {
      const time = new Date(bar.Datetime).getTime() / 1000;
      
      if (bar.long_entries === true) {
        const emaDiff = (bar.EMA_8 - bar.VWMA_20).toFixed(5);
        const threshold = bar.long_threshold?.toFixed(5) || "N/A";
        
        longSignals.push({
          time,
          position: "belowBar" as const,
          color: bullColor,
          shape: "circle" as const,
          text: `LONG | Th:${threshold} | Diff:${emaDiff}`,
          size: 2,
        });
      }
      
      if (bar.short_entries === true) {
        const emaDiff = (bar.EMA_8 - bar.VWMA_20).toFixed(5);
        const threshold = bar.short_threshold?.toFixed(5) || "N/A";
        
        shortSignals.push({
          time,
          position: "aboveBar" as const,
          color: bearColor,
          shape: "circle" as const,
          text: `SHORT | Th:${threshold} | Diff:${emaDiff}`,
          size: 2,
        });
      }
    }

    const allSignals = [...longSignals, ...shortSignals].sort((a, b) => a.time - b.time);

    if (allSignals.length > 0) {
      candleSeries.setMarkers(allSignals);
      console.log("✅ Set", allSignals.length, "signal markers on candlestick series");
    }
  }, [candleSeries, indicators, showMarkers]);
};