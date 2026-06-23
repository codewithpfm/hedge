import { useEffect, useState } from "react";
import { useChartSeries } from "../hooks";
import type { IChartApi } from "lightweight-charts";
import { FaCircle } from "react-icons/fa";
import { oneLine } from "common-tags";

type IndicatorProps = {
  keyName: string;
  name: string;
  color: string;
  chart: IChartApi | null;
  data: Record<string, any>[];
};

export const Indicator = ({
  keyName,
  name,
  color,
  chart,
  data,
}: IndicatorProps) => {
  const [show, setShow] = useState(true);
  const [seriesChart, setSeriesChart] = useState<any>();

  const series = data
    ?.filter((_d) => _d[keyName])
    ?.map((_d) => ({
      time: new Date(_d.Datetime).getTime() / 1000,
      value: _d[keyName],
    }));

  useEffect(() => {
    if(!chart) return;

    if (show) {
      const _seriesChart = useChartSeries({
        chart: chart,
        data: series,
        seriesOptions: {
          color: color,
        },
      });

      setSeriesChart(_seriesChart);
    } 
    
    if(!show && seriesChart){
      seriesChart && chart?.removeSeries(seriesChart);
    }
  }, [show]);
  

  return <>
    <div className={oneLine`
                        flex 
                        justify-between 
                        items-center 
                        bg-white 
                        p-1 
                        text-neutral-600 
                        m-1 
                        w-[200px] 
                        cursor-pointer
                        rounded
                      `} 
          onClick={() => setShow(!show)}>
      <span className="text-sm" style={{color: color}}>{name}</span>
      <FaCircle height={24} width={24} color={show ? color : "#11111130"} />
    </div>
  </>
};
