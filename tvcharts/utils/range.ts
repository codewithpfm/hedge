export type RangePreset =
  | "1M"
  | "3M"
  | "6M"
  | "1Y"
  | "1.5Y"
  | "2Y"
  | "2.5Y"
  | "3Y"
  | "5Y"
  | "ALL"
  | "CUSTOM";

export const PRESET_OPTIONS: { key: RangePreset; label: string }[] = [
  { key: "1M", label: "1 Month" },
  { key: "3M", label: "3 Months" },
  { key: "6M", label: "6 Months" },
  { key: "1Y", label: "1 Year" },
  { key: "1.5Y", label: "1.5 Years" },
  { key: "2Y", label: "2 Years" },
  { key: "2.5Y", label: "2.5 Years" },
  { key: "3Y", label: "3 Years" },
  { key: "5Y", label: "5 Years" },
  { key: "ALL", label: "ALL" },
  { key: "CUSTOM", label: "Custom" },
];

export type StatsBounds = {
  min_datetime: string;
  max_datetime: string; 
};

export type DateRange = {
  start: string;
  end: string; 
};

function toYMD(input: string | Date): string {
  const d = input instanceof Date ? input : new Date(input);
  return d.toISOString().slice(0, 10);
}

function addMonths(ymd: string, months: number): string {
  const d = new Date(ymd + "T00:00:00Z");
  d.setUTCMonth(d.getUTCMonth() + months);
  return toYMD(d);
}

function addYears(ymd: string, years: number): string {
  const d = new Date(ymd + "T00:00:00Z");
  d.setUTCFullYear(d.getUTCFullYear() + years);
  return toYMD(d);
}

export function clampToBounds(range: DateRange, bounds: StatsBounds): DateRange {
  const min = toYMD(bounds.min_datetime);
  const max = toYMD(bounds.max_datetime);

  let start = range.start;
  let end = range.end;

  if (start < min) start = min;
  if (end > max) end = max;
  if (end < start) end = start;

  return { start, end };
}

export function computeRangeFromPreset(preset: RangePreset, bounds: StatsBounds): DateRange {
  const start = toYMD(bounds.min_datetime);
  let end: string;

  switch (preset) {
    case "1M":
      end = addMonths(start, 1);
      break;
    case "3M":
      end = addMonths(start, 3);
      break;
    case "6M":
      end = addMonths(start, 6);
      break;
    case "1Y":
      end = addYears(start, 1);
      break;
    case "1.5Y":
      end = addMonths(start, 18);
      break;
    case "2Y":
      end = addYears(start, 2);
      break;
    case "2.5Y":
      end = addMonths(start, 30);
      break;
    case "3Y":
      end = addYears(start, 3);
      break;
    case "5Y":
      end = addYears(start, 5);
      break;
    case "ALL":
      end = toYMD(bounds.max_datetime);
      return { start, end };
    default:
      end = addMonths(start, 1);
  }

  return clampToBounds({ start, end }, bounds);
}

export function validateRange(start: string, end: string): { ok: boolean; error: string } {
  if (!start || !end) return { ok: false, error: "Select both start and end dates." };
  const s = new Date(start);
  const e = new Date(end);
  if (Number.isNaN(s.getTime()) || Number.isNaN(e.getTime())) {
    return { ok: false, error: "Invalid date(s)." };
  }
  if (e < s) return { ok: false, error: "End date must be after start date." };
  return { ok: true, error: "" };
}

export function diffDays(start: string, end: string): number {
  const s = new Date(start).getTime();
  const e = new Date(end).getTime();
  return Math.floor((e - s) / (1000 * 60 * 60 * 24));
}