import { useEffect, useState } from "react";
import { createChart, CrosshairMode } from "lightweight-charts";
import type { IChartApi, DeepPartial, ChartOptions } from "lightweight-charts";

interface TVChartsProps {
  ref: HTMLElement | null;
  chartOptions?: DeepPartial<ChartOptions>;
}

export const useTVCharts = ({ ref, chartOptions = {} }: TVChartsProps) => {
  const [chart, setChart] = useState<IChartApi | null>(null);

  useEffect(() => {
    if (!ref) return;

    // Clear the container
    ref.innerHTML = "";

    const getCSSVariable = (varName: string, fallback: string): string => {
      if (typeof window === 'undefined') return fallback;
      const styles = getComputedStyle(document.documentElement);
      const value = styles.getPropertyValue(varName).trim();
      return value || fallback;
    };

    const textColor = getCSSVariable('--chart-text', '#262626');
    const backgroundColor = getCSSVariable('--chart-bg', '#ffffff');
    const crosshairColor = getCSSVariable('--chart-crosshair', '#9B7DFF');
    const borderColor = getCSSVariable('--chart-border', '#71649C');

    const newChart = createChart(ref, {
      layout: {
        textColor: textColor,
        background: { color: backgroundColor },
      },
      ...chartOptions,
    });

    newChart.applyOptions({
      crosshair: {
        mode: CrosshairMode.Normal,
        horzLine: {
          color: crosshairColor,
          labelBackgroundColor: crosshairColor,
        },
      },
    });

    newChart.timeScale().applyOptions({
      borderColor: borderColor,
      timeVisible: true,
    });

    setChart(newChart);

    // Cleanup on unmount or ref change
    return () => {
      newChart.remove();
      setChart(null);
    };
  }, [ref]); // Only re-run if the container element changes

  return chart;
};
