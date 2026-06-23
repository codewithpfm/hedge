import { useMemo } from "react";
import {
  RangePreset,
  DateRange,
  StatsBounds,
  validateRange,
  diffDays,
} from "../utils/range";

interface UseRangeNavigationParams {
  preset: RangePreset;
  rangeBox: DateRange;
  bounds: StatsBounds | null;
  setRangeBox: React.Dispatch<React.SetStateAction<DateRange>>;
}

export const useRangeNavigation = ({
  preset,
  rangeBox,
  bounds,
  setRangeBox,
}: UseRangeNavigationParams) => {
  const navigateRange = (direction: "prev" | "next") => {
    if (!bounds) return;

    const stepSize = preset === "ALL" || preset === "CUSTOM" ? "1M" : preset;
    const currentStart = new Date(rangeBox.start + "T00:00:00Z");
    const currentEnd = new Date(rangeBox.end + "T00:00:00Z");

    let newStart: Date;
    let newEnd: Date;

    let monthsToShift = 0;
    switch (stepSize) {
      case "1M": monthsToShift = 1; break;
      case "3M": monthsToShift = 3; break;
      case "6M": monthsToShift = 6; break;
      case "1Y": monthsToShift = 12; break;
      case "1.5Y": monthsToShift = 18; break;
      case "2Y": monthsToShift = 24; break;
      case "2.5Y": monthsToShift = 30; break;
      case "3Y": monthsToShift = 36; break;
      case "5Y": monthsToShift = 60; break;
    }

    if (direction === "next") {
      newStart = new Date(currentStart);
      newStart.setUTCMonth(newStart.getUTCMonth() + monthsToShift);
      newEnd = new Date(currentEnd);
      newEnd.setUTCMonth(newEnd.getUTCMonth() + monthsToShift);
    } else {
      newStart = new Date(currentStart);
      newStart.setUTCMonth(newStart.getUTCMonth() - monthsToShift);
      newEnd = new Date(currentEnd);
      newEnd.setUTCMonth(newEnd.getUTCMonth() - monthsToShift);
    }

    const minDate = new Date(bounds.min_datetime);
    const maxDate = new Date(bounds.max_datetime);

    if (newStart < minDate) newStart = minDate;
    if (newEnd > maxDate) newEnd = maxDate;

    const newRange = {
      start: newStart.toISOString().slice(0, 10),
      end: newEnd.toISOString().slice(0, 10),
    };

    setRangeBox(newRange);
  };

  const canNavigatePrev = useMemo(() => {
    if (!bounds || !rangeBox.start) return false;
    return rangeBox.start > bounds.min_datetime.slice(0, 10);
  }, [bounds, rangeBox.start]);

  const canNavigateNext = useMemo(() => {
    if (!bounds || !rangeBox.end) return false;
    return rangeBox.end < bounds.max_datetime.slice(0, 10);
  }, [bounds, rangeBox.end]);

  const rangeValidation = useMemo(() => {
    if (preset === "ALL") return { ok: true, error: "" };
    return validateRange(rangeBox.start, rangeBox.end);
  }, [preset, rangeBox.start, rangeBox.end]);

  return {
    navigateRange,
    canNavigatePrev,
    canNavigateNext,
    rangeValidation,
  };
};