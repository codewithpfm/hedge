//tvcharts/components/trading/SignalsCard.tsx
import { Signal } from "../../types/trading";

interface SignalsCardProps {
  signals: Signal[];
  collapsed: boolean;
  setCollapsed: (collapsed: boolean) => void;
  onSignalClick: (datetime: string) => void;
  showOnChart: boolean;
  setShowOnChart: (show: boolean) => void;
}

const formatExitReason = (type: string): string => {
  return type === "long" ? "LONG" : "SHORT";
};

const getSignalColor = (type: string): string => {
  return type === "long" ? "text-green-600" : "text-red-600";
};

export const SignalsCard: React.FC<SignalsCardProps> = ({
  signals,
  collapsed,
  setCollapsed,
  onSignalClick,
  showOnChart,
  setShowOnChart,
}) => {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex justify-between items-center mb-3">
        <div
          className="flex-1 cursor-pointer"
          onClick={() => setCollapsed(!collapsed)}
        >
          <h2 className="text-sm font-semibold text-gray-700">
            All Signals ({signals.length})
          </h2>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowOnChart(!showOnChart);
            }}
            className={`text-xs px-3 py-1 rounded transition-colors ${
              showOnChart
                ? "bg-blue-500 text-white hover:bg-blue-600"
                : "bg-gray-200 text-gray-700 hover:bg-gray-300"
            }`}
          >
            {showOnChart ? "Hide" : "Show"} on Chart
          </button>
          <span
            className="text-gray-500 text-sm cursor-pointer"
            onClick={() => setCollapsed(!collapsed)}
          >
            {collapsed ? "▼" : "▲"}
          </span>
        </div>
      </div>
      {!collapsed && (
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {signals.map((signal, idx) => (
            <div
              key={idx}
              onClick={() => onSignalClick(signal.datetime)}
              className="text-xs border-b border-gray-100 pb-2 last:border-0 cursor-pointer hover:bg-gray-50 transition-colors px-2 py-1 rounded"
            >
              <div className="flex justify-between mb-1">
                <span className={`font-medium ${getSignalColor(signal.type)}`}>
                  #{idx + 1} {formatExitReason(signal.type)}
                </span>
                <span className="text-gray-500">
                  {new Date(signal.datetime).toLocaleDateString()}
                </span>
              </div>
              <div className="text-gray-600 flex justify-between items-center text-[10px]">
                <span>Threshold: {signal.threshold}</span>
                <span>Diff: {signal.ema_diff}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};