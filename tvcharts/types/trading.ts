//tvcharts/types/trading.ts
export interface Trade {
  entry_date: string;
  exit_date: string;
  entry_price: number;
  exit_price: number;
  exit_reason: string;
  pnl: number;
  return: number;
  type: string;
  size: number;
  // Bias snapshot at entry — populated by trades.parquet from the strategy's
  // bias engine. Optional so older runs without these columns don't break.
  session_date?: string;
  bias?: string;
  bullish_score?: number;
  bearish_score?: number;
  tie_broken?: boolean;
  adx_active?: boolean;
  vote_ema50?: string;
  vote_rsi?: string;
  vote_macd?: string;
  vote_pdh_pdl?: string;
  vote_vwap?: string;
  atr?: number;
  ema50?: number;
  rsi?: number;
  macd_hist?: number;
  adx?: number;
  di_pos?: number;
  di_neg?: number;
  prev_high?: number;
  prev_low?: number;
  prev_close?: number;
  ref_price?: number;
  vwap?: number;
  entry_close?: number;
}

export interface Signal {
  datetime: string;
  type: "long" | "short";
  threshold: string;
  ema_diff: string;
}

export interface Run {
  id: string;        // directory name, e.g. "EURUSD_london_20260525_192056"
  ticker: string;
  session: string;
  start: string;
  end: string;
  created_at: string;
  starting_balance_usd?: number;
  leverage?: number;
  risk_percent?: number;
}

export interface Candle {
  Datetime: string;
  Open: number;
  High: number;
  Low: number;
  Close: number;
}

export interface ChartCandle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
}

// Indicator series available on the chart. Backed by columns in
// runs/{id}/indicators.parquet produced by scripts/dump_indicators.py.
// Overlays render on the price chart; subplots render in their own pane.
export const INDICATOR_OVERLAYS = [
  "ema50",
  "vwap",
  "prev_high",
  "prev_low",
  "prev_close",
] as const;

export const INDICATOR_SUBPLOTS = ["atr", "adx"] as const;

export type IndicatorOverlay = (typeof INDICATOR_OVERLAYS)[number];
export type IndicatorSubplot = (typeof INDICATOR_SUBPLOTS)[number];
export type IndicatorName = IndicatorOverlay | IndicatorSubplot;

export const INDICATOR_LABEL: Record<IndicatorName, string> = {
  ema50: "EMA(50) — daily",
  vwap: "Session VWAP",
  prev_high: "Prev Day High",
  prev_low: "Prev Day Low",
  prev_close: "Prev Day Close",
  atr: "ATR(14) — daily",
  adx: "ADX(14) — daily",
};

export const INDICATOR_COLOR: Record<IndicatorName, string> = {
  ema50: "#D17B0F",
  vwap: "#1f77b4",
  prev_high: "#008800",
  prev_low: "#cc0000",
  prev_close: "#666666",
  atr: "#8e44ad",
  adx: "#2c3e50",
};

export const isOverlay = (n: IndicatorName): n is IndicatorOverlay =>
  (INDICATOR_OVERLAYS as readonly string[]).includes(n);

export const isSubplot = (n: IndicatorName): n is IndicatorSubplot =>
  (INDICATOR_SUBPLOTS as readonly string[]).includes(n);

export interface IndicatorRow {
  Datetime: string;
  ema50?: number | null;
  vwap?: number | null;
  prev_high?: number | null;
  prev_low?: number | null;
  prev_close?: number | null;
  atr?: number | null;
  adx?: number | null;
}
