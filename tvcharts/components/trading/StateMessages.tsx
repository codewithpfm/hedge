import { RangePreset, DateRange, StatsBounds } from "../../utils/range";

interface StateMessagesProps {
  bounds: StatsBounds | null;
  hasError: boolean;
  statsError: any;
  sigError: any;
  checkError: any;
  isLoading: boolean;
  preset: RangePreset;
  rangeBox: DateRange;
  isEmpty: boolean;
  hasData: boolean;
}

export const StateMessages: React.FC<StateMessagesProps> = ({
  bounds,
  hasError,
  statsError,
  sigError,
  checkError,
  isLoading,
  preset,
  rangeBox,
  isEmpty,
  hasData,
}) => {
  if (!bounds && !hasError) {
    return (
      <div className="flex items-center justify-center h-[95vh] bg-neutral-50 rounded-lg border-2 border-dashed border-neutral-300">
        <div className="text-center max-w-md px-4">
          <div className="animate-spin text-6xl mb-4">⏳</div>
          <h2 className="text-xl font-semibold text-neutral-700 mb-2">
            Loading run stats...
          </h2>
          <p className="text-sm text-neutral-500 mt-4">
            Check console for diagnostic info if this persists.
          </p>
        </div>
      </div>
    );
  }

  if (bounds && isLoading) {
    return (
      <div className="flex items-center justify-center h-[95vh] bg-blue-50 rounded-lg border-2 border-blue-200">
        <div className="text-center max-w-md px-4">
          <div className="animate-spin text-7xl mb-4">⏳</div>
          <h2 className="text-2xl font-semibold text-blue-700 mb-2">
            Loading Charts...
          </h2>
          <p className="text-base text-blue-600 mb-3">
            {preset === "ALL"
              ? "Fetching ALL data"
              : `Fetching data from ${rangeBox.start} to ${rangeBox.end}`}
          </p>
        </div>
      </div>
    );
  }

  if (hasError) {
    return (
      <div className="flex items-center justify-center h-[95vh] bg-red-50 rounded-lg border-2 border-red-200">
        <div className="text-center max-w-md px-4">
          <div className="text-6xl mb-4">⚠️</div>
          <h2 className="text-xl font-semibold text-red-700 mb-2">
            Failed to Load Data
          </h2>
          <p className="text-sm text-red-600 mb-4">
            {statsError?.message ||
              sigError?.message ||
              checkError?.message ||
              "Unknown error occurred"}
          </p>
        </div>
      </div>
    );
  }

  if (isEmpty) {
    return (
      <div className="flex items-center justify-center h-[95vh] bg-yellow-50 rounded-lg border-2 border-yellow-200">
        <div className="text-center max-w-md px-4">
          <div className="text-6xl mb-4">🔍</div>
          <h2 className="text-xl font-semibold text-yellow-700 mb-2">
            No Data Found
          </h2>
          <p className="text-sm text-yellow-600 mb-4">
            No candles exist in the selected range.
          </p>
        </div>
      </div>
    );
  }

  return null;
};