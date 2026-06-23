# strategy.py
from typing import Literal
from scipy.stats import zscore
import pandas as pd
import numpy as np


def generate_signals(ema, vwma):
    """
    Generates the signals for the calculation of the divergences
    """
    entries = np.logical_and(ema.shift(1) < vwma.shift(1), ema > vwma)
    exits = np.logical_and((ema.shift(1) > vwma.shift(1)), (ema < vwma))
    short_entries = np.logical_and((ema.shift(1) > vwma.shift(1)), (ema < vwma))
    short_exits = np.logical_and((ema.shift(1) < vwma.shift(1)), (ema > vwma))

    return entries, exits, short_entries, short_exits


def calc_divergences(close, high, low, entries, exits, _type="long"):
    """
    Calculates Divergences, based on the direction of the entry anfd exit signals
    """
    divisions = np.where(entries, 1, np.where(exits, -1, 0))
    start = 0
    lowest = 0
    highest = 0

    changes = []
    entry_dt = None
    exit_dt = None

    for index in range(0, len(divisions) - 1):
        row = divisions[index]

        if row == 1:
            entry_dt = close.index[index]
            start = close[index]
            lowest = low[index]
            highest = high[index]

        if entry_dt is not None and (row == 0 or row == -1):
            _highest = high[index]
            _lowest = low[index]

            lowest = _lowest if _lowest < lowest else lowest
            highest = _highest if _highest > highest else highest

        if entry_dt is not None and row == -1:
            exit_dt = close.index[index]
            changes.append([entry_dt, exit_dt, start, lowest, highest])
            lowest = 0
            highest = 0
            entry_dt = None
            exit_dt = None

    df = pd.DataFrame(
        changes[1:-1], columns=["entry_dt", "exit_dt", "start", "low", "high"]
    )
    positive_change = (df["high"] - df["start"]) / df["start"]
    negative_change = (df["start"] - df["low"]) / df["start"]
    df["tp_change"] = positive_change if _type == "long" else negative_change
    df["sl_change"] = negative_change if _type == "long" else positive_change

    return df


def calc_sl_tp(sl_series, tp_series):
    """
    Calculates the Stop Loss and Take Profit based on the series of changes
    """
    sl = sl_series[sl_series > 0]
    tp = tp_series[tp_series > 0]

    sl = sl[np.abs(zscore(sl)) < 3]
    tp = tp[np.abs(zscore(tp)) < 3]

    return sl.quantile(0.15), tp.quantile(0.7)


def calc_sltp_percent(data, fast_average: str, slow_average: str, direction: Literal["long", "short"]) -> tuple[float, float]:
    """
    Wrapper function to calculate the Stop Loss and Take Profit based on the data
    """
    if not direction:
        raise ValueError("Direction is required")
    
    close = data["Close"]
    high = data["High"]
    low = data["Low"]
    fast = data[fast_average]
    slow = data[slow_average]

    entries, exits, short_entries, short_exits = generate_signals(fast, slow)

    if direction == "long":
        long_divergences = calc_divergences(close, high, low, entries, exits, _type="long")
        long_sl, long_tp = calc_sl_tp(
            long_divergences["sl_change"], long_divergences["tp_change"]
        )
        return long_sl, long_tp
    
    if direction == "short":
        short_divergences = calc_divergences(
            close, high, low, short_entries, short_exits, _type="short"
        )
        short_sl, short_tp = calc_sl_tp(
            short_divergences["sl_change"], short_divergences["tp_change"]
        )
        return short_sl, short_tp