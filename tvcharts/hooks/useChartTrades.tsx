import type { IChartApi, Time } from "lightweight-charts";
import { bullColor, bearColor } from "./useLoadCandles";

type ChartTradeProps = {
  chart: IChartApi | null;
  data: Array<{
    time: Time;
    value: number;
    type: "long" | "short";
    label?: string;   // optional extra text shown on the entry marker (e.g. bias)
  }>[];
};

export const useChartTrades = ({ chart, data }: ChartTradeProps) => {
  if (!data?.length || !chart) return;

  for (const index in data) {
    const current = data[index];
    const color = current[0].type === "long" ? bullColor : bearColor;

    const lineSeries = chart.addLineSeries({
      color,
      lineWidth: 0.5 as any,
      priceLineVisible: false,
    });

    lineSeries.setData(
      current.map((p: any) => ({ time: p.time, value: p.value }))
    );

    lineSeries.setMarkers(
      current.map((p: any, i: number) => {
        const isEntry = i === 0;
        const base = isEntry ? `entry @${p.value}` : `exit @${p.value}`;
        const text = isEntry && p.label ? `${base} · ${p.label}` : base;
        return {
          time: p.time,
          position: "aboveBar",
          color,
          shape: isEntry ? "arrowDown" : "arrowUp",
          text,
        };
      })
    );
  }
};
