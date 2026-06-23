// Trade detail modal — shows everything trades.parquet has on one trade:
// entry/exit, bias votes, indicator snapshot at entry, P&L. The trade's row
// already carries the bias engine's full state at entry time, so no extra
// fetch is needed.

import type { Trade } from "../../types/trading";

interface TradeDetailModalProps {
  trade: Trade | null;
  onClose: () => void;
}

const fmt = (v: number | undefined, digits = 5) =>
  v === undefined || v === null ? "—" : v.toFixed(digits);

const fmtMoney = (v: number | undefined) =>
  v === undefined || v === null ? "—" : v.toLocaleString(undefined, { maximumFractionDigits: 2 });

const fmtDate = (s: string | undefined) =>
  s ? new Date(s).toLocaleString() : "—";

const biasColor = (bias: string | undefined) => {
  if (!bias) return "text-gray-500";
  if (bias.includes("STRONG_BULLISH")) return "text-green-700 font-semibold";
  if (bias.includes("WEAK_BULLISH")) return "text-green-600";
  if (bias.includes("STRONG_BEARISH")) return "text-red-700 font-semibold";
  if (bias.includes("WEAK_BEARISH")) return "text-red-600";
  return "text-gray-600";
};

const voteColor = (v: string | undefined) => {
  if (v === "bullish") return "text-green-600";
  if (v === "bearish") return "text-red-600";
  if (v === "abstain") return "text-gray-400 italic";
  return "text-gray-500";
};

export const TradeDetailModal: React.FC<TradeDetailModalProps> = ({
  trade,
  onClose,
}) => {
  if (!trade) return null;

  const pnlColor = trade.pnl >= 0 ? "text-green-600" : "text-red-600";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex justify-between items-center px-5 py-3 border-b sticky top-0 bg-white">
          <div className="flex items-baseline gap-3">
            <span
              className={
                trade.type === "long"
                  ? "text-green-600 font-bold text-lg"
                  : "text-red-600 font-bold text-lg"
              }
            >
              {trade.type?.toUpperCase()}
            </span>
            <span className={`text-sm ${biasColor(trade.bias)}`}>
              {trade.bias ?? "—"}
            </span>
            <span className="text-xs text-gray-500">
              session {trade.session_date ?? "—"}
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-700 text-xl leading-none"
            title="Close"
          >
            ×
          </button>
        </div>

        <div className="px-5 py-4 space-y-4 text-sm">
          {/* Entry / exit */}
          <section>
            <h3 className="text-xs uppercase text-gray-500 mb-1">Trade</h3>
            <div className="grid grid-cols-2 gap-x-6 gap-y-1">
              <div>
                <span className="text-gray-500">Entry:</span>{" "}
                <span className="font-mono">{fmt(trade.entry_price)}</span>{" "}
                <span className="text-gray-400 text-xs">@ {fmtDate(trade.entry_date)}</span>
              </div>
              <div>
                <span className="text-gray-500">Exit:</span>{" "}
                <span className="font-mono">{fmt(trade.exit_price)}</span>{" "}
                <span className="text-gray-400 text-xs">@ {fmtDate(trade.exit_date)}</span>
              </div>
              <div>
                <span className="text-gray-500">Size:</span>{" "}
                <span className="font-mono">{fmtMoney(trade.size)}</span>
              </div>
              <div>
                <span className="text-gray-500">Exit reason:</span>{" "}
                <span className="font-medium">{trade.exit_reason}</span>
              </div>
              <div>
                <span className="text-gray-500">P&amp;L:</span>{" "}
                <span className={`font-mono ${pnlColor}`}>{fmtMoney(trade.pnl)}</span>
              </div>
              <div>
                <span className="text-gray-500">Return:</span>{" "}
                <span className={`font-mono ${pnlColor}`}>
                  {trade.return !== undefined
                    ? `${(trade.return * 100).toFixed(3)}%`
                    : "—"}
                </span>
              </div>
            </div>
          </section>

          {/* Bias votes */}
          <section>
            <h3 className="text-xs uppercase text-gray-500 mb-1">Bias engine</h3>
            <div className="grid grid-cols-2 gap-x-6 gap-y-1">
              <div>
                <span className="text-gray-500">Score:</span>{" "}
                <span className="text-green-700">{trade.bullish_score ?? "—"}</span>
                <span className="text-gray-400"> bull / </span>
                <span className="text-red-700">{trade.bearish_score ?? "—"}</span>
                <span className="text-gray-400"> bear</span>
              </div>
              <div>
                <span className="text-gray-500">Tie-broken:</span>{" "}
                {trade.tie_broken ? "yes" : "no"}
              </div>
              <div>
                <span className="text-gray-500">ADX active:</span>{" "}
                {trade.adx_active ? (
                  <span className="text-green-600">yes</span>
                ) : (
                  <span className="text-gray-400">no</span>
                )}
              </div>
            </div>
            <div className="grid grid-cols-5 gap-2 mt-2 text-xs">
              {(
                ["vote_ema50", "vote_rsi", "vote_macd", "vote_pdh_pdl", "vote_vwap"] as const
              ).map((v) => (
                <div key={v} className="text-center bg-gray-50 rounded p-1">
                  <div className="text-gray-500 text-[10px]">
                    {v.replace("vote_", "")}
                  </div>
                  <div className={voteColor(trade[v] as any)}>
                    {trade[v] ?? "—"}
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Indicator snapshot at entry */}
          <section>
            <h3 className="text-xs uppercase text-gray-500 mb-1">
              Indicators at entry
            </h3>
            <div className="grid grid-cols-3 gap-x-4 gap-y-1 font-mono text-xs">
              <div><span className="text-gray-500">EMA50:</span> {fmt(trade.ema50)}</div>
              <div><span className="text-gray-500">VWAP:</span> {fmt(trade.vwap)}</div>
              <div><span className="text-gray-500">ATR:</span> {fmt(trade.atr)}</div>
              <div><span className="text-gray-500">RSI:</span> {fmt(trade.rsi, 3)}</div>
              <div><span className="text-gray-500">ADX:</span> {fmt(trade.adx, 2)}</div>
              <div><span className="text-gray-500">MACD hist:</span> {fmt(trade.macd_hist, 5)}</div>
              <div><span className="text-gray-500">+DI:</span> {fmt(trade.di_pos, 3)}</div>
              <div><span className="text-gray-500">-DI:</span> {fmt(trade.di_neg, 3)}</div>
              <div><span className="text-gray-500">Entry close:</span> {fmt(trade.entry_close)}</div>
              <div><span className="text-gray-500">Prev high:</span> {fmt(trade.prev_high)}</div>
              <div><span className="text-gray-500">Prev low:</span> {fmt(trade.prev_low)}</div>
              <div><span className="text-gray-500">Prev close:</span> {fmt(trade.prev_close)}</div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
};
