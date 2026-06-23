import pandas as pd


def train_test_split(df, train_percent):
    """
    Split the data into training and testing dataframes
    """
    length = len(df)
    split_index = int((train_percent * length) / 100)

    return df[:split_index], df[split_index:]


def combine_series(cols, *args):
    """
    Convert pandas series into a dataframe
    """

    series_list = []

    for arg in args:
        series_list.append(arg.to_frame())

    df = pd.concat(series_list, axis=1)
    df.columns = cols

    return df

def clear_anomalies(df):
    """
    Remove anomalies from the dataframe
    """
    df.sort_index()
    return df[~df.index.duplicated(keep="first")]


def trades_to_returns(trades: list, init_cash: float) -> pd.Series:
    """
    Convert list of closed trades into a daily returns series for quantstats.
    P&L is attributed to the exit_date (trade closed = realized that day).
    """
    if not trades:
        return pd.Series(dtype=float)

    trades_df = pd.DataFrame(trades)
    trades_df["exit_date"] = pd.to_datetime(trades_df["exit_date"]).dt.normalize()  # floor to day

    # Sum P&L per day (multiple trades can close on same day)
    daily_pnl = trades_df.groupby("exit_date")["pnl"].sum()

    # Build full date range from first entry to last exit
    all_dates = pd.date_range(
        start=pd.to_datetime(trades_df["entry_date"].min()).normalize(),
        end=pd.to_datetime(trades_df["exit_date"].max()).normalize(),
        freq="D",
    )

    daily_pnl = daily_pnl.reindex(all_dates, fill_value=0.0)

    # Build equity curve: cumulative sum of P&L on top of init_cash
    equity_curve = init_cash + daily_pnl.cumsum()

    # Daily returns = equity[t] / equity[t-1] - 1
    daily_returns = equity_curve.pct_change().dropna()

    # Give it a clean name
    daily_returns.name = "Strategy"
    daily_returns.index.name = "Date"

    return daily_returns