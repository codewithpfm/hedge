import { useEffect, useState } from "react";
import type { IChartApi, Time, CandlestickData, ISeriesApi } from "lightweight-charts";

type LoadCandlesProps = {
    chart: IChartApi | null;
    candles: CandlestickData<Time>[] | undefined;
};

export const bullColor = "#26a69acc";
export const bearColor = "#ef5350cc";

export const useLoadCandles = ({chart, candles}: LoadCandlesProps) => {
    const [series, setSeries] = useState<ISeriesApi<"Candlestick"> | null>(null);

    useEffect(() => {
        if (!chart || !candles || candles.length === 0) {
            setSeries(null);
            return;
        }

        const candlestickSeries = chart.addCandlestickSeries({
          upColor: bullColor,
          downColor: bearColor,
          borderVisible: false,
          wickUpColor: bullColor,
          wickDownColor: bearColor,
          priceLineVisible: false,
          priceFormat: {
            type: "price",
            precision: 5,
            minMove: 0.00001,
          },
        });

        candlestickSeries.setData(candles);
        setSeries(candlestickSeries);

        return () => {
          try {
            chart.removeSeries(candlestickSeries);
          } catch (e) {
            // Chart might have been removed already
          }
          setSeries(null);
        };
    }, [chart, candles]);

    return series;
};