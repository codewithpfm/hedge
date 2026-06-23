import pandas as pd
import numpy as np

from typing import Literal
from .sltp import calc_sltp_percent

class Trainer:
    def __init__(self, data):
        self.data = data

    def calc_threshold(
        self, fast_average: str, slow_average: str, direction: Literal["long", "short"]
    ) -> float:
        if not direction:
            raise Exception("Direction is required")

        # Calculate differences
        def remove_outliers(change):
            return change

            Q1 = change.quantile(0.25)
            Q3 = change.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR

            df_no_outliers = change[(change >= lower_bound) & (change <= upper_bound)]

            return df_no_outliers

        df = pd.DataFrame()
        df["fast"] = self.data[fast_average]
        df["slow"] = self.data[slow_average]
        df["diff"] = df["slow"] - df["fast"]
        df["change"] = df["diff"].pct_change()

        if direction == "long":
            df["long_crossover"] = np.logical_and(
                df["fast"] > df["slow"], df["fast"].shift() < df["slow"].shift()
            )
            # Get indices one step before crossover
            long_indices = [
                i - 1 for i, row in enumerate(df["long_crossover"] == True) if row
            ]
            # Filter rows based on indices
            long_rows = df.iloc[long_indices]
            long_diffs = remove_outliers(abs(long_rows["diff"]))
            self.long_threshold = long_diffs.quantile(0.75)

            # Remove outliers
            # long_diffs_pct = remove_outliers(abs(long_rows['change']))
            return long_diffs.quantile(0.75)

        if direction == "short":
            df["short_crossover"] = np.logical_and(
                df["fast"] < df["slow"], df["fast"].shift() > df["slow"].shift()
            )
            # Get indices one step before crossover
            short_indices = [
                i - 1 for i, row in enumerate(df["short_crossover"] == True) if row
            ]
            # Filter rows based on indices
            short_rows = df.iloc[short_indices]
            short_diffs = remove_outliers(abs(short_rows["diff"]))
            self.short_threshold = short_diffs.quantile(0.75)

            # Remove outliers
            # short_diffs_pct = remove_outliers(abs(short_rows['change']))
            return short_diffs.quantile(0.75)

    def calc_sltp_pct(
        self, fast_average: str, slow_average: str, direction: Literal["long", "short"]
    ) -> tuple[float, float]:
        # Ensure this returns the correct tuple as expected by the method's contract
        return calc_sltp_percent(self.data, fast_average, slow_average, direction)
