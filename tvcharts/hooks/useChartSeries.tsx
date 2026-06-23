import type {
  IChartApi,
  LineData,
  Time,
  DeepPartial,
  LineStyleOptions,
  WhitespaceData,
  SeriesOptionsCommon,
} from "lightweight-charts";

type ChartSeriesProps = {
  chart: IChartApi | null;
  data: {
    time: number;
    value: number;
  }[];
  seriesOptions?: DeepPartial<LineStyleOptions & SeriesOptionsCommon>;
};

export const useChartSeries = ({
  chart,
  data,
  seriesOptions,
}: ChartSeriesProps) => {
  if (!chart || !data) return;

  const series = chart.addLineSeries({
    color: "green",
    lineWidth: 1,
    ...seriesOptions,
    priceLineVisible: false,
  });

  series.setData(data as any);

  return series;
};
