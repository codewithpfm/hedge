import { formatStatKey, formatStatValue } from "../../utils/formatters";

interface StatsCardProps {
  stats: any[];
  collapsed: boolean;
  setCollapsed: (collapsed: boolean) => void;
}

export const StatsCard: React.FC<StatsCardProps> = ({
  stats,
  collapsed,
  setCollapsed,
}) => {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div
        className="flex justify-between items-center cursor-pointer mb-3"
        onClick={() => setCollapsed(!collapsed)}
      >
        <h2 className="text-sm font-semibold text-gray-700">Backtest Stats</h2>
        <span className="text-gray-500 text-sm">{collapsed ? "▼" : "▲"}</span>
      </div>
      {!collapsed && (
        <div className="space-y-2 text-xs">
          {Object.entries(stats[0] || {})
            .slice(0, 10)
            .map(([key, value]) => (
              <div key={key} className="flex justify-between">
                <span className="text-gray-600">{formatStatKey(key)}:</span>
                <span className="font-medium text-gray-900">
                  {formatStatValue(key, value)}
                </span>
              </div>
            ))}
        </div>
      )}
    </div>
  );
};