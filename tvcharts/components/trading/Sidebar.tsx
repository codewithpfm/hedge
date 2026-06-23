//tvcharts/components/trading/Sidebar.tsx
import { StatsCard } from "./StatsCard";
import { TradesCard } from "./TradesCard";
import { SignalsCard } from "./SignalsCard";
import { Trade, Signal } from "../../types/trading";

interface SidebarProps {
  stats: any[] | null;
  trades: Trade[] | null;
  signals: Signal[] | null;
  statsCollapsed: boolean;
  setStatsCollapsed: (collapsed: boolean) => void;
  tradesCollapsed: boolean;
  setTradesCollapsed: (collapsed: boolean) => void;
  signalsCollapsed: boolean;
  setSignalsCollapsed: (collapsed: boolean) => void;
  showSignalsOnChart: boolean;
  setShowSignalsOnChart: (show: boolean) => void;
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (collapsed: boolean) => void;
  onSignalClick: (datetime: string) => void;
  onTradeClick?: (trade: Trade) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  stats,
  trades,
  signals,
  statsCollapsed,
  setStatsCollapsed,
  tradesCollapsed,
  setTradesCollapsed,
  signalsCollapsed,
  setSignalsCollapsed,
  showSignalsOnChart,
  setShowSignalsOnChart,
  sidebarCollapsed,
  setSidebarCollapsed,
  onSignalClick,
  onTradeClick,
}) => {
  if (!stats || stats.length === 0) return null;

  return (
    <>
      <aside
        className={[
          "flex-shrink-0 transition-all duration-300 ease-in-out",
          sidebarCollapsed ? "w-0" : "w-80",
        ].join(" ")}
      >
        {!sidebarCollapsed && (
          <div className="space-y-4">
            <StatsCard
              stats={stats}
              collapsed={statsCollapsed}
              setCollapsed={setStatsCollapsed}
            />

            {trades && trades.length > 0 && (
              <TradesCard
                trades={trades}
                collapsed={tradesCollapsed}
                setCollapsed={setTradesCollapsed}
                onTradeClick={onTradeClick}
              />
            )}

            {signals && signals.length > 0 && (
              <SignalsCard
                signals={signals}
                collapsed={signalsCollapsed}
                setCollapsed={setSignalsCollapsed}
                onSignalClick={onSignalClick}
                showOnChart={showSignalsOnChart}
                setShowOnChart={setShowSignalsOnChart}
              />
            )}
          </div>
        )}
      </aside>

      <button
        onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
        className="flex-shrink-0 bg-white border border-gray-300 rounded px-2 py-4 text-lg hover:bg-gray-50 transition-colors self-start mt-2"
        title={sidebarCollapsed ? "Show stats & trades" : "Hide stats & trades"}
      >
        {sidebarCollapsed ? "▶" : "◀"}
      </button>
    </>
  );
};