// Sync the visible time range across multiple lightweight-charts instances.
// When the user pans/zooms one chart, the others follow. Subplot panes use
// this to stay aligned with the main price chart.

import { useEffect } from "react";
import type { IChartApi } from "lightweight-charts";

export const useChartTimeSync = (charts: (IChartApi | null)[]) => {
  useEffect(() => {
    const active = charts.filter((c): c is IChartApi => c !== null);
    if (active.length < 2) return;

    let suppressed = false;
    const unsubs = active.map((chart, idx) => {
      const handler = (range: any) => {
        if (suppressed || !range) return;
        suppressed = true;
        try {
          for (let j = 0; j < active.length; j++) {
            if (j === idx) continue;
            active[j].timeScale().setVisibleRange(range);
          }
        } catch {
          /* lightweight-charts throws when a range falls outside data; ignore */
        } finally {
          suppressed = false;
        }
      };
      chart.timeScale().subscribeVisibleTimeRangeChange(handler);
      return () => chart.timeScale().unsubscribeVisibleTimeRangeChange(handler);
    });

    return () => {
      for (const u of unsubs) {
        try { u(); } catch {}
      }
    };
  }, [charts]);
};
