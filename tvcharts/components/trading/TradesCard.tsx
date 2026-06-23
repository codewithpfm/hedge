import type { Trade } from "../../types/trading";

interface TradesCardProps {
  trades: Trade[];
  collapsed: boolean;
  setCollapsed: (collapsed: boolean) => void;
  onTradeClick?: (trade: Trade) => void;
}

const formatExitReason = (reason: string | undefined): string => {
  if (!reason || reason === "unknown") return "—";

  const reasonMap: Record<string, string> = {
    // legacy single-position-strategy reasons
    hard_stop_loss: "Hard SL",
    dynamic_stop_loss: "Dynamic SL",
    take_profit: "TP",
    trend_flip: "Trend Flip",
    invalid_htf_trend: "Invalid HTF",
    invalid_4h_trend: "Invalid HTF",
    // current Nautilus strategy reasons pass through unchanged (SL / TP /
    // max-hold 23h / SESSION_END), so no mapping needed
  };

  return reasonMap[reason] || reason;
};

const getReasonColor = (reason: string | undefined): string => {
  if (!reason) return "text-gray-500";
  if (reason === "SL" || reason.includes("stop_loss")) return "text-red-600";
  if (reason === "TP" || reason === "take_profit") return "text-green-600";
  if (reason.startsWith("max-hold")) return "text-amber-600";
  if (reason.includes("trend")) return "text-yellow-600";
  return "text-gray-600";
};

export const TradesCard: React.FC<TradesCardProps> = ({
  trades,
  collapsed,
  setCollapsed,
  onTradeClick,
}) => {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div
        className="flex justify-between items-center cursor-pointer mb-3"
        onClick={() => setCollapsed(!collapsed)}
      >
        <h2 className="text-sm font-semibold text-gray-700">
          All Trades ({trades.length})
        </h2>
        <span className="text-gray-500 text-sm">{collapsed ? "▼" : "▲"}</span>
      </div>
      {!collapsed && (
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {trades.map((trade, idx) => {
            const clickable = !!onTradeClick;
            return (
              <div
                key={idx}
                className={[
                  "text-xs border-b border-gray-100 pb-2 last:border-0",
                  clickable
                    ? "cursor-pointer hover:bg-gray-50 px-1 -mx-1 rounded transition-colors"
                    : "",
                ].join(" ")}
                onClick={clickable ? () => onTradeClick!(trade) : undefined}
                title={clickable ? "Click to navigate + view details" : undefined}
              >
                <div className="flex justify-between mb-1">
                  <span
                    className={
                      trade.type === "long"
                        ? "text-green-600 font-medium"
                        : "text-red-600 font-medium"
                    }
                  >
                    #{idx + 1} {trade.type?.toUpperCase()}
                  </span>
                  <span className="text-gray-500">
                    {new Date(trade.entry_date).toLocaleDateString()}
                  </span>
                </div>
                <div className="text-gray-600 flex justify-between items-center">
                  <span>
                    Entry: {trade.entry_price?.toFixed(5)} → Exit:{" "}
                    {trade.exit_price?.toFixed(5)}
                  </span>
                  <span className={`font-medium ${getReasonColor(trade.exit_reason)}`}>
                    {formatExitReason(trade.exit_reason)}
                  </span>
                </div>
                {trade.bias && (
                  <div className="text-[10px] text-gray-400 mt-0.5">
                    {trade.bias}
                    {trade.pnl !== undefined && (
                      <span
                        className={`ml-2 ${
                          trade.pnl >= 0 ? "text-green-600" : "text-red-600"
                        }`}
                      >
                        {trade.pnl >= 0 ? "+" : ""}
                        {trade.pnl.toFixed(0)}
                      </span>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
