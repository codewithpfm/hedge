import sys
import pendulum
import pandas as pd


sys.path.append("..")
from .handlers.parquet import ParquetHandler
from config import POLYGON_API_KEY
from .urls import get_ticker

# Tickers Polygon doesn't cover on the current plan — route these through MT5
# via storelib.mt5_source.fetch_mt5, which returns the same Polygon-shape
# DataFrame so the rest of the cache pipeline is unchanged.
_MT5_ONLY_SYMBOLS = {"XAUUSD"}


class Fetcher:
    def __init__(self, dir = "store"):
        self.pq = ParquetHandler(f"./.{dir}")

    def fetch(self, symbol, start, end):
        print(f"Fetching {symbol}: {start} -> {end}")

        start = start.format("YYYY-MM-DD")
        end = end.format("YYYY-MM-DD")

        base = symbol.split(":", 1)[1] if ":" in symbol else symbol
        if base in _MT5_ONLY_SYMBOLS:
            from .mt5_source import fetch_mt5
            return fetch_mt5(symbol, start, end)

        data = get_ticker(symbol, start, end)

        return data

    def get_data(self, symbol, start, end):
        print(f"Checking Datastore: [{symbol}]")

        start = pendulum.parse(start)
        end = pendulum.parse(end)

        # Load Tickers, if none is present add current one.
        tickers = None
        try:
            tickers = self.pq.load("tickers").to_dict("records")
        except FileNotFoundError:
            tickers = []

        tick = None
        for _tick in tickers:
            if _tick["ticker"] == symbol:
                tick = _tick

        if tick is None:
            data = self.fetch(symbol, start, end)
            tick = {
                "ticker": symbol,
                "start": start.isoformat(),
                "end": end.isoformat(),
            }

            tickers.append(tick)
            self.pq.save(symbol, data)

        if tick is not None:
            _start = pendulum.parse(tick["start"])
            _end = pendulum.parse(tick["end"])

            startDiff = _start.diff(start, False).in_minutes()
            endDiff = _end.diff(end, False).in_minutes()

            if startDiff == 0 and endDiff == 0:
                self.pq.load(symbol)

            if startDiff < 0 or endDiff > 0:
                current_block = self.pq.load(symbol)
                start_block = pd.DataFrame([])
                end_block = pd.DataFrame([])

                if startDiff < 0:
                    start_block = self.fetch(symbol, start, _start)
                    tick["start"] = start.isoformat()

                if endDiff > 0:
                    end_block = self.fetch(symbol, _end, end)
                    tick["end"] = end.isoformat()

                merged = pd.concat([start_block, current_block, end_block])

                for t in tickers:
                    if t["ticker"] == symbol:
                        t = tick

                merged = merged.sort_index()
                self.pq.save(symbol, merged)

        self.pq.save("tickers", pd.DataFrame(tickers))
        data = self.pq.load(symbol)

        return data[start:end]

    def get(self, symbol: str | list[str], start: str, end: str):
        if isinstance(symbol, str):
            return self.get_data(symbol, start, end)
        elif isinstance(symbol, list):
            data = {}
            for s in symbol:
                data[s] = self.get_data(s, start, end)
            return data

        else:
            raise ValueError("Symbol must be a string or a list of strings")