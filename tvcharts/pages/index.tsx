//tvcharts/pages/index.tsx
import { useState, useEffect, useRef, useMemo } from "react";
import { oneLine } from "common-tags";
import {
  useTVCharts,
  useLoadCandles,
  useChartTrades,
  useChartTimeSync,
} from "../hooks";
import {
  PRESET_OPTIONS,
  type RangePreset,
  computeRangeFromPreset,
  type DateRange,
} from "../utils/range";
import { extractBounds } from "../utils/statsExtractor";
import { Header } from "../components/trading/Header";
import { Sidebar } from "../components/trading/Sidebar";
import { StateMessages } from "../components/trading/StateMessages";
import { TradeDetailModal } from "../components/trading/TradeDetailModal";
import type { Trade } from "../types/trading";
import { useTradingData } from "../hooks/useTradingData";
import { useRangeNavigation } from "../hooks/useRangeNavigation";
import type { Timeframe } from "../fetchers/candles";
import {
  INDICATOR_COLOR,
  INDICATOR_LABEL,
  isOverlay,
  isSubplot,
} from "../types/trading";
import type { IndicatorName } from "../types/trading";

const twPageStyles = oneLine`
  pb-2
  h-full
  w-full
`;

const Home = () => {
  const [chartContainer, setChartContainer] = useState<HTMLElement | null>(null);
  const [atrContainer, setAtrContainer] = useState<HTMLElement | null>(null);
  const [adxContainer, setAdxContainer] = useState<HTMLElement | null>(null);
  const chart = useTVCharts({ ref: chartContainer });
  const atrChart = useTVCharts({ ref: atrContainer });
  const adxChart = useTVCharts({ ref: adxContainer });

  const [runId, setRunId] = useState<string | null>(null);
  const [runs, setRuns] = useState<any[]>([]);
  const [tf, setTf] = useState<Timeframe>("1m");
  const [preset, setPreset] = useState<RangePreset>("1M");
  const [rangeBox, setRangeBox] = useState<DateRange>({ start: "", end: "" });
  const [statsCollapsed, setStatsCollapsed] = useState(false);
  const [tradesCollapsed, setTradesCollapsed] = useState(false);
  const [signalsCollapsed, setSignalsCollapsed] = useState(false);
  const [showSignalsOnChart, setShowSignalsOnChart] = useState(true);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [selectedIndicators, setSelectedIndicators] = useState<IndicatorName[]>([]);

  const toggleIndicator = (name: IndicatorName) => {
    setSelectedIndicators((prev) =>
      prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name]
    );
  };

  const selectedSubplots = useMemo(
    () => selectedIndicators.filter(isSubplot),
    [selectedIndicators]
  );
  const showAtr = selectedSubplots.includes("atr");
  const showAdx = selectedSubplots.includes("adx");

  const queryRange = useMemo(() => {
    return { start: rangeBox.start || null, end: rangeBox.end || null };
  }, [rangeBox.start, rangeBox.end]);

  const canFetchCandles =
    runId !== null &&
    (preset === "ALL" || (!!rangeBox.start && !!rangeBox.end));

  const {
    runners,
    stats,
    statsLoading,
    statsError,
    candles,
    candlesLoading,
    candlesError,
    trades,
    allTrades,
    indicators,
  } = useTradingData({
    runId,
    tf,
    queryRange,
    canFetchCandles,
    selectedIndicators,
  });

  // Click handler — pan chart to the trade and open the detail modal. If the
  // trade is outside the current rangeBox, widen the box so candles get
  // re-fetched (this is what powers the visual "fly to" behaviour).
  const [tradeDetail, setTradeDetail] = useState<Trade | null>(null);
  const handleTradeClick = (trade: Trade) => {
    setTradeDetail(trade);

    const entryDateStr = trade.entry_date.split("T")[0];
    const exitDateStr = trade.exit_date.split("T")[0];

    // Build a window that comfortably contains the trade (a few days either
    // side so the surrounding context is visible) and re-fetch candles for it.
    const pad = 2;   // days padding
    const fromDate = new Date(entryDateStr);
    fromDate.setDate(fromDate.getDate() - pad);
    const toDate = new Date(exitDateStr);
    toDate.setDate(toDate.getDate() + pad);

    const newRange = {
      start: fromDate.toISOString().split("T")[0],
      end: toDate.toISOString().split("T")[0],
    };
    if (newRange.start !== rangeBox.start || newRange.end !== rangeBox.end) {
      setRangeBox(newRange);
    }

    // Ask the chart to center on the entry once new candles land. Calling
    // setVisibleRange immediately would race the candles re-fetch, so defer.
    if (chart) {
      const entryTs = new Date(trade.entry_date).getTime() / 1000;
      const span = 6 * 3600;
      setTimeout(() => {
        try {
          chart.timeScale().setVisibleRange({
            from: (entryTs - span) as any,
            to: (entryTs + span) as any,
          });
        } catch {
          /* range may still be outside loaded data — silently skip */
        }
      }, 300);
    }
  };

  const bounds = useMemo(() => extractBounds(stats), [stats]);

  const {
    navigateRange,
    canNavigatePrev,
    canNavigateNext,
    rangeValidation,
  } = useRangeNavigation({
    preset,
    rangeBox,
    bounds,
    setRangeBox,
  });

  useEffect(() => {
    if (!runners) return;
    const run = runners.latest;
    if (!run) return;
    setRunId(run.id);
    setRuns(runners.runs);
  }, [runners]);

  useEffect(() => {
    if (!bounds) return;
    setPreset("1M");

    // Start from the last month instead of the first month — defaults to the
    // most recent slice of the run, which is what you usually want to inspect.
    const endDate = new Date(bounds.max_datetime);
    const startDate = new Date(endDate);
    startDate.setMonth(startDate.getMonth() - 1);

    setRangeBox({
      start: startDate.toISOString().split("T")[0],
      end: endDate.toISOString().split("T")[0],
    });
  }, [bounds?.min_datetime, bounds?.max_datetime]);

  useEffect(() => {
    if (!bounds || !rangeBox.start || !rangeBox.end) return;

    for (const option of PRESET_OPTIONS) {
      if (option.key === "CUSTOM") continue;
      const testRange = computeRangeFromPreset(option.key, bounds);
      if (rangeBox.start === testRange.start && rangeBox.end === testRange.end) {
        if (preset !== option.key) setPreset(option.key);
        return;
      }
    }

    if (preset !== "CUSTOM") setPreset("CUSTOM");
  }, [rangeBox.start, rangeBox.end]);

  const applyPreset = (p: RangePreset) => {
    setPreset(p);
    if (!bounds) return;
    if (p === "CUSTOM") return;
    setRangeBox(computeRangeFromPreset(p, bounds));
  };

  const candlesMemo = useMemo(() => {
    return candles?.map((candle: any) => ({
      time: new Date(candle.Datetime).getTime() / 1000,
      open: candle.Open,
      high: candle.High,
      low: candle.Low,
      close: candle.Close,
    }));
  }, [candles]);

  const candleSeries = useLoadCandles({ chart, candles: candlesMemo });

  useEffect(() => {
    if (chart && candles && candles.length > 0) {
      const t = setTimeout(() => chart.timeScale().fitContent(), 100);
      return () => clearTimeout(t);
    }
  }, [chart, candles]);

  useEffect(() => {
    if (!chart) return;
    const timer = setTimeout(() => chart.timeScale().fitContent(), 350);
    return () => clearTimeout(timer);
  }, [sidebarCollapsed, chart]);

  // Render selected price-overlay indicators on the main chart. Subplot
  // indicators (ATR/ADX) are handled separately below on their own panes.
  useEffect(() => {
    if (!chart || !indicators || indicators.length === 0) return;
    const seriesList: any[] = [];
    for (const name of selectedIndicators) {
      if (!isOverlay(name)) continue;
      const data = indicators
        .filter((r: any) => r[name] != null)
        .map((r: any) => ({
          time: new Date(r.Datetime).getTime() / 1000,
          value: r[name],
        }));
      if (data.length === 0) continue;
      const series = chart.addLineSeries({
        color: INDICATOR_COLOR[name],
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      series.setData(data);
      seriesList.push(series);
    }
    return () => {
      for (const s of seriesList) {
        try { chart.removeSeries(s); } catch {}
      }
    };
  }, [chart, indicators, selectedIndicators.join(",")]);

  // Subplot panes — one chart instance per oscillator. Each renders its own
  // line series so the price scale matches the indicator's range
  // (ATR in price units vs ADX in 0-100).
  useEffect(() => {
    if (!showAtr || !atrChart || !indicators || indicators.length === 0) return;
    const data = indicators
      .filter((r: any) => r.atr != null)
      .map((r: any) => ({
        time: new Date(r.Datetime).getTime() / 1000,
        value: r.atr,
      }));
    if (data.length === 0) return;
    const series = atrChart.addLineSeries({
      color: INDICATOR_COLOR.atr,
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: true,
    });
    series.setData(data);
    const t = setTimeout(() => atrChart.timeScale().fitContent(), 100);
    return () => {
      clearTimeout(t);
      try { atrChart.removeSeries(series); } catch {}
    };
  }, [atrChart, indicators, showAtr]);

  useEffect(() => {
    if (!showAdx || !adxChart || !indicators || indicators.length === 0) return;
    const data = indicators
      .filter((r: any) => r.adx != null)
      .map((r: any) => ({
        time: new Date(r.Datetime).getTime() / 1000,
        value: r.adx,
      }));
    if (data.length === 0) return;
    const series = adxChart.addLineSeries({
      color: INDICATOR_COLOR.adx,
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: true,
    });
    series.setData(data);
    const t = setTimeout(() => adxChart.timeScale().fitContent(), 100);
    return () => {
      clearTimeout(t);
      try { adxChart.removeSeries(series); } catch {}
    };
  }, [adxChart, indicators, showAdx]);

  // Keep all visible chart panes pan/zoomed together.
  useChartTimeSync([
    chart,
    showAtr ? atrChart : null,
    showAdx ? adxChart : null,
  ]);

  // Build the per-trade marker payload. Bias label is appended to the entry
  // marker text so the user can read it without leaving the chart.
  const tradeMarkers = useMemo(() => {
    return trades?.map((trade: any) => {
      const entry = {
        time: new Date(trade.entry_date).getTime() / 1000,
        value: trade.entry_price,
        type: trade.type,
        label: trade.bias,   // e.g. "STRONG_BULLISH"
      };
      const exit = {
        time: new Date(trade.exit_date).getTime() / 1000,
        value: trade.exit_price,
        type: trade.type,
      };
      return [entry, exit];
    });
  }, [trades]);

  useChartTrades({ chart, data: tradeMarkers });

  const isLoading = statsLoading || candlesLoading;
  const hasError = !!(statsError || candlesError);
  const hasData = !!(canFetchCandles && candles);
  const isEmpty = !!(hasData && candles && candles.length === 0);

  // Indicator-derived signals are no longer emitted by the strategy; keep the
  // sidebar's Signals card hidden by passing an empty list.
  const signals: any[] = [];

  const handleSignalClick = (_datetime: string) => {};

  return (
    <div className={twPageStyles}>
      <Header
        runId={runId}
        runs={runs}
        setRunId={setRunId}
        tf={tf}
        setTf={setTf}
        preset={preset}
        applyPreset={applyPreset}
        bounds={bounds}
        rangeBox={rangeBox}
        setRangeBox={setRangeBox}
        navigateRange={navigateRange}
        canNavigatePrev={canNavigatePrev}
        canNavigateNext={canNavigateNext}
        isLoading={isLoading}
        rangeValidation={rangeValidation}
        selectedIndicators={selectedIndicators}
        toggleIndicator={toggleIndicator}
      />

      <main className="px-2 flex gap-2">
        <Sidebar
          stats={stats}
          trades={allTrades ?? trades}
          signals={signals}
          statsCollapsed={statsCollapsed}
          setStatsCollapsed={setStatsCollapsed}
          tradesCollapsed={tradesCollapsed}
          setTradesCollapsed={setTradesCollapsed}
          signalsCollapsed={signalsCollapsed}
          setSignalsCollapsed={setSignalsCollapsed}
          showSignalsOnChart={showSignalsOnChart}
          setShowSignalsOnChart={setShowSignalsOnChart}
          sidebarCollapsed={sidebarCollapsed}
          setSidebarCollapsed={setSidebarCollapsed}
          onSignalClick={handleSignalClick}
          onTradeClick={handleTradeClick}
        />

        <div className="flex-1">
          <StateMessages
            bounds={bounds}
            hasError={hasError}
            statsError={statsError}
            sigError={candlesError}
            checkError={null}
            isLoading={isLoading}
            preset={preset}
            rangeBox={rangeBox}
            isEmpty={isEmpty}
            hasData={hasData}
          />

          {isEmpty && (
            <div className="flex items-center justify-center h-[50vh] bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
              <div className="text-center p-8">
                <p className="text-xl font-semibold text-gray-700 mb-2">
                  No data in selected date range
                </p>
                <p className="text-gray-500 mb-4">
                  {rangeBox.start} to {rangeBox.end}
                </p>
                <button
                  onClick={() => applyPreset("ALL")}
                  className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-lg transition-colors"
                >
                  View All Data
                </button>
              </div>
            </div>
          )}

          {hasData && !isEmpty && (
            <div className="relative min-h-[90vh] flex flex-col gap-1">
              <section
                ref={setChartContainer}
                className={
                  showAtr || showAdx
                    ? "w-full min-h-[300px] h-[55vh]"
                    : "w-full min-h-[500px] h-[85vh]"
                }
              ></section>

              {showAtr && (
                <div className="w-full">
                  <div className="text-[11px] text-gray-500 px-2 pt-1">
                    {INDICATOR_LABEL.atr}
                  </div>
                  <section
                    ref={setAtrContainer}
                    className="w-full h-[18vh] min-h-[120px]"
                  ></section>
                </div>
              )}

              {showAdx && (
                <div className="w-full">
                  <div className="text-[11px] text-gray-500 px-2 pt-1">
                    {INDICATOR_LABEL.adx}
                  </div>
                  <section
                    ref={setAdxContainer}
                    className="w-full h-[18vh] min-h-[120px]"
                  ></section>
                </div>
              )}
            </div>
          )}
        </div>
      </main>

      <TradeDetailModal trade={tradeDetail} onClose={() => setTradeDetail(null)} />
    </div>
  );
};

export default Home;
