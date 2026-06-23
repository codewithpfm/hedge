"""
This file contains the backtest handler class.
This class is responsible for handling data from the backtest process.
"""

import os
from datetime import datetime
import pandas as pd


class BacktestDataHandler:
    """
    Class that handles the data from the backtest process.
    """

    def __init__(self, data_handler) -> None:
        self.data_handler = data_handler

        runners = pd.DataFrame(columns=["id", "run_at"])

        try:
            runners = self.data_handler.load("runners")
            self.run_id = (runners["id"].iloc[-1] or 0) + 1

        except FileNotFoundError:
            self.run_id = 0

        finally:
            df = pd.DataFrame({"id": [self.run_id], "run_at": [datetime.now()]})
            runners = pd.concat([runners, df], ignore_index=True)
            self.data_handler.save("runners", runners)

        self.data_dir = f"data/{self.run_id}"
        os.makedirs(self.data_dir)

    def get_run_id(self):
        """
        Get the run ID.
        """
        return self.run_id

    def save_params(self, params):
        """
        Save the candles data.
        """
        self.data_handler.save(f"{self.run_id}/params", params)

    def save_candles(self, candles, tf):
        """
        Save the candles data.
        """
        self.data_handler.save(f"{self.run_id}/candles_{tf}", candles)

    def save_indicators(self, indicators, tf):
        """
        Save the candles data.
        """
        self.data_handler.save(f"{self.run_id}/indicators_{tf}", indicators)

    def save_trades(self, trades):
        """
        Save the trades data.
        """
        self.data_handler.save(f"{self.run_id}/trades", trades)

    def process_and_save_trades(self, trades, data, fees):
        """
        Process trades by adding exit reasons and fees, then save.
        """
        if not trades:
            return

        trades_df = pd.DataFrame(trades)

        def get_exit_reason(row):
            """Look up exit reason from signals_df based on exit_date and trade type"""
            try:
                exit_dt = pd.to_datetime(row['exit_date'])
                trade_type = row['type']
                if exit_dt in data.index:
                    bar = data.loc[exit_dt]
                    reason_col = f"sigs_{trade_type}_exit_reason"
                    reason = bar.get(reason_col, "")
                    return reason if reason and not pd.isna(reason) else "unknown"
                return "unknown"
            except Exception:
                return "unknown"

        trades_df['exit_reason'] = trades_df.apply(get_exit_reason, axis=1)
        trades_df = trades_df[
            [
                "entry_date",
                "exit_date",
                "entry_price",
                "exit_price",
                "exit_reason",
                "pnl",
                "return",
                "type",
                "quantity",
            ]
        ].copy()

        trades_df.rename(columns={"quantity": "size"}, inplace=True)
        trades_df["entry_fees"] = trades_df["size"] / 100000 * fees
        trades_df["exit_fees"] = trades_df["size"] / 100000 * fees
        trades_df["fees"] = trades_df["entry_fees"] + trades_df["exit_fees"]
        trades_df["gross_pnl"] = trades_df["pnl"]
        trades_df["pnl"] = trades_df["gross_pnl"] - trades_df["fees"]

        self.save_trades(trades_df)
        return trades_df

    def save_stats(self, stats):
        """
        Save the stats data.
        """
        self.data_handler.save(f"{self.run_id}/stats", stats)
