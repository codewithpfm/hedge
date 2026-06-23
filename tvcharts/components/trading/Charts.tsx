import { useRef } from "react";

interface ChartsProps {
  hasData: boolean;
  isEmpty: boolean;
}

export const Charts: React.FC<ChartsProps> = ({ hasData, isEmpty }) => {
  const ref = useRef<HTMLElement>(null);
  const checkRef = useRef<HTMLElement>(null);

  if (!hasData || isEmpty) return null;

  return (
    <div className="relative min-h-[95vh]">
      <section ref={ref} className="h-[55vh] w-full min-h-[400px]"></section>
      <section
        ref={checkRef}
        className="h-[40vh] w-full min-h-[300px]"
        onScroll={(event) => event.stopPropagation()}
      ></section>
    </div>
  );
};

export { useRef as useChartRef };