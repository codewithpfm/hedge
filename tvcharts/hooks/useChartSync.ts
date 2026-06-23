//tvcharts/hooks/useChartSync.ts
import { useEffect } from "react";

interface UseChartSyncParams {
  chart: any;
  checkChart: any;
  sigCandleSeries: any;
  checkCandleSeries: any;
}

export const useChartSync = ({
  chart,
  checkChart,
  sigCandleSeries,
  checkCandleSeries,
}: UseChartSyncParams) => {
  useEffect(() => {
    if (!chart || !checkChart) return;
    if (!sigCandleSeries || !checkCandleSeries) return;

    function getCrosshairDataPoint(series: any, param: any) {
      if (!param?.time) return null;
      return param.seriesData.get(series) || null;
    }

    function syncCrosshair(_chart: any, _series: any, dataPoint: any) {
      // For candlestick series, 'value' will be undefined, but it has 'close'
      const price = dataPoint?.value ?? dataPoint?.close;
      const time = dataPoint?.time;

      if (dataPoint && price !== undefined && time !== undefined) {
        try {
          _chart.setCrosshairPosition(price, time, _series);
        } catch (e) {
          // Silently ignore crosshair sync errors
        }
      } else {
        try {
          _chart.clearCrosshairPosition();
        } catch (e) {
          // Silently ignore crosshair clear errors
        }
      }
    }
    const unsub1 = chart.subscribeCrosshairMove((param: any) => {
      const dataPoint = getCrosshairDataPoint(sigCandleSeries, param);
      syncCrosshair(checkChart, checkCandleSeries, dataPoint);
    });

    const unsub2 = checkChart.subscribeCrosshairMove((param: any) => {
      const dataPoint = getCrosshairDataPoint(checkCandleSeries, param);
      syncCrosshair(chart, sigCandleSeries, dataPoint);
    });

    return () => {
      try {
        // @ts-ignore
        if (typeof unsub1 === "function") unsub1();
        // @ts-ignore
        if (typeof unsub2 === "function") unsub2();
      } catch {}
    };
  }, [chart, checkChart, sigCandleSeries, checkCandleSeries]);
};