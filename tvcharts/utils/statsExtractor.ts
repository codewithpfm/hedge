import { StatsBounds } from "./range";

function pickFirstObject(stats: any) {
  if (!stats) return null;
  if (Array.isArray(stats)) return stats[0] ?? null;
  return stats;
}

export function extractBounds(stats: any): StatsBounds | null {
  console.log("[extractBounds] raw input:", stats);
  
  const s = pickFirstObject(stats);
  console.log("[extractBounds] after pickFirstObject:", s);
  
  if (!s || typeof s !== "object") {
    console.warn("[extractBounds] Invalid stats object:", s);
    return null;
  }

  console.log("[extractBounds] available keys:", Object.keys(s));

  const min =
    s["Start Index"] ??
    s.min_datetime ??
    s.minDatetime ??
    s.min_date ??
    s.minDate ??
    s.start_datetime ??
    s.startDatetime ??
    s.start_date ??
    s.startDate ??
    s.start ??
    s.from ??
    s.first_date ??
    s.firstDate ??
    s.first_datetime ??
    s.firstDatetime ??
    null;

  const max =
    s["End Index"] ??
    s.max_datetime ??
    s.maxDatetime ??
    s.max_date ??
    s.maxDate ??
    s.end_datetime ??
    s.endDatetime ??
    s.end_date ??
    s.endDate ??
    s.end ??
    s.to ??
    s.last_date ??
    s.lastDate ??
    s.last_datetime ??
    s.lastDatetime ??
    null;

  console.log("[extractBounds] extracted min:", min, "max:", max);

  if (!min || !max) {
    console.error(
      "[extractBounds] ⚠️ Could not find min/max dates in stats. Available keys:",
      Object.keys(s),
      "\nFull object:",
      s
    );
    return null;
  }
  
  const bounds = { min_datetime: String(min), max_datetime: String(max) };
  console.log("[extractBounds] ✅ final bounds:", bounds);
  return bounds;
}