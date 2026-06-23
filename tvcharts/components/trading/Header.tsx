import { Popover, PopoverButton, PopoverPanel } from "@headlessui/react";
import {
  PRESET_OPTIONS,
  diffDays,
} from "../../utils/range";
import type { RangePreset, DateRange, StatsBounds } from "../../utils/range";
import type { Run, IndicatorName } from "../../types/trading";
import {
  INDICATOR_OVERLAYS,
  INDICATOR_SUBPLOTS,
  INDICATOR_LABEL,
  INDICATOR_COLOR,
} from "../../types/trading";
import { TIMEFRAMES } from "../../fetchers/candles";
import type { Timeframe } from "../../fetchers/candles";

interface HeaderProps {
  runId: string | null;
  runs: Run[];
  setRunId: (id: string) => void;
  tf: Timeframe;
  setTf: (tf: Timeframe) => void;
  preset: RangePreset;
  applyPreset: (p: RangePreset) => void;
  bounds: StatsBounds | null;
  rangeBox: DateRange;
  setRangeBox: React.Dispatch<React.SetStateAction<DateRange>>;
  navigateRange: (direction: "prev" | "next") => void;
  canNavigatePrev: boolean;
  canNavigateNext: boolean;
  isLoading: boolean;
  rangeValidation: { ok: boolean; error: string };
  selectedIndicators: IndicatorName[];
  toggleIndicator: (name: IndicatorName) => void;
}

export const Header: React.FC<HeaderProps> = ({
  runId,
  runs,
  setRunId,
  tf,
  setTf,
  preset,
  applyPreset,
  bounds,
  rangeBox,
  setRangeBox,
  navigateRange,
  canNavigatePrev,
  canNavigateNext,
  isLoading,
  rangeValidation,
  selectedIndicators,
  toggleIndicator,
}) => {
  const selectedSet = new Set(selectedIndicators);
  const showLargeRangeHint =
    preset !== "ALL" &&
    rangeValidation.ok &&
    rangeBox.start &&
    rangeBox.end &&
    diffDays(rangeBox.start, rangeBox.end) > 90;

  return (
    <header className="p-2 flex items-center justify-between bg-neutral-100 sticky top-0 left-0 z-20 gap-3">
      <div className="flex items-center gap-3 flex-wrap">
        <span className="font-semibold">TV Charts</span>

        {/* Run Selector */}
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-600">Run:</label>
          <select
            value={runId ?? ""}
            onChange={(e) => setRunId(e.target.value)}
            className="px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {runs.map((run) => (
              <option key={run.id} value={run.id}>
                {run.ticker} / {run.session} — {new Date(run.created_at).toLocaleDateString()}
              </option>
            ))}
          </select>
        </div>

        {/* Timeframe Selector */}
        <div className="flex items-center gap-2 border-l border-gray-300 pl-3">
          <label className="text-xs text-gray-600">TF:</label>
          <select
            value={tf}
            onChange={(e) => setTf(e.target.value as Timeframe)}
            className="px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {TIMEFRAMES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>

        {/* Presets Dropdown */}
        <div className="flex items-center gap-2 border-l border-gray-300 pl-3">
          <label className="text-xs text-gray-600">Range:</label>
          <select
            value={preset}
            onChange={(e) => applyPreset(e.target.value as RangePreset)}
            disabled={!bounds}
            className="px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {PRESET_OPTIONS.map((p) => (
              <option key={p.key} value={p.key}>
                {p.label}
              </option>
            ))}
          </select>
        </div>

        {/* Range Box with Navigation Arrows */}
        <div className="flex items-center gap-2 border-l border-gray-300 pl-3">
          <button
            onClick={() => navigateRange("prev")}
            disabled={!canNavigatePrev || preset === "ALL"}
            className={[
              "px-2 py-1 text-sm rounded border transition-colors",
              canNavigatePrev && preset !== "ALL"
                ? "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
                : "bg-gray-100 text-gray-400 border-gray-200 cursor-not-allowed",
            ].join(" ")}
            title="Previous period"
          >
            ←
          </button>

          <div className="flex items-center gap-2 bg-white border border-gray-300 rounded px-2 py-1">
            <span className="text-[11px] text-gray-500">From</span>
            <input
              type="date"
              value={rangeBox.start}
              onChange={(e) => {
                setRangeBox((prev) => ({ ...prev, start: e.target.value }));
              }}
              className="text-xs focus:outline-none"
              disabled={!bounds || preset === "ALL"}
            />
            <span className="text-[11px] text-gray-500">to</span>
            <input
              type="date"
              value={rangeBox.end}
              onChange={(e) => {
                setRangeBox((prev) => ({ ...prev, end: e.target.value }));
              }}
              className="text-xs focus:outline-none"
              disabled={!bounds || preset === "ALL"}
            />
          </div>

          <button
            onClick={() => navigateRange("next")}
            disabled={!canNavigateNext || preset === "ALL"}
            className={[
              "px-2 py-1 text-sm rounded border transition-colors",
              canNavigateNext && preset !== "ALL"
                ? "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
                : "bg-gray-100 text-gray-400 border-gray-200 cursor-not-allowed",
            ].join(" ")}
            title="Next period"
          >
            →
          </button>

          <span className="text-[11px] text-gray-500 flex items-center gap-1">
            {isLoading && <span className="animate-spin">⏳</span>}
            {preset === "ALL"
              ? "Applied: ALL"
              : rangeBox.start && rangeBox.end
              ? `Applied: ${rangeBox.start} → ${rangeBox.end}`
              : "Applied: —"}
          </span>
        </div>

        {!rangeValidation.ok && preset !== "ALL" && (
          <div className="text-xs text-red-600 bg-red-50 px-2 py-1 rounded border border-red-200">
            {rangeValidation.error}
          </div>
        )}

        {showLargeRangeHint && (
          <div className="text-xs text-yellow-700 bg-yellow-50 px-2 py-1 rounded border border-yellow-200">
            Large range may be slow.
          </div>
        )}
      </div>

      {/* Indicator picker — multi-select popover. Selected names are passed
          back to pages/index.tsx which adds a LineSeries per overlay. */}
      <div className="flex items-center gap-2">
        <Popover className="relative">
          <PopoverButton className="px-2 py-1 text-sm border border-gray-300 rounded bg-white hover:bg-gray-50 focus:outline-none">
            Indicators
            {selectedIndicators.length > 0 && (
              <span className="ml-1 inline-block bg-blue-500 text-white text-[10px] leading-4 rounded-full w-4 h-4 text-center">
                {selectedIndicators.length}
              </span>
            )}
          </PopoverButton>
          <PopoverPanel
            anchor="bottom end"
            className="z-30 mt-1 bg-white border border-gray-200 rounded shadow-lg p-2 min-w-[220px]"
          >
            <div className="text-[11px] text-gray-500 px-1 pb-1 border-b mb-1">
              Price-chart overlays
            </div>
            {INDICATOR_OVERLAYS.map((name) => (
              <label
                key={name}
                className="flex items-center gap-2 text-sm px-1 py-1 hover:bg-gray-50 cursor-pointer rounded"
              >
                <input
                  type="checkbox"
                  checked={selectedSet.has(name)}
                  onChange={() => toggleIndicator(name)}
                />
                <span
                  className="inline-block w-3 h-[2px]"
                  style={{ background: INDICATOR_COLOR[name] }}
                />
                <span>{INDICATOR_LABEL[name]}</span>
              </label>
            ))}
            <div className="text-[11px] text-gray-500 px-1 pt-2 pb-1 border-b mb-1 mt-1">
              Subplots
            </div>
            {INDICATOR_SUBPLOTS.map((name) => (
              <label
                key={name}
                className="flex items-center gap-2 text-sm px-1 py-1 hover:bg-gray-50 cursor-pointer rounded"
              >
                <input
                  type="checkbox"
                  checked={selectedSet.has(name)}
                  onChange={() => toggleIndicator(name)}
                />
                <span
                  className="inline-block w-3 h-[2px]"
                  style={{ background: INDICATOR_COLOR[name] }}
                />
                <span>{INDICATOR_LABEL[name]}</span>
              </label>
            ))}
          </PopoverPanel>
        </Popover>
      </div>
    </header>
  );
};
