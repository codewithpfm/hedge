import MetaTrader5 as mt5 # type: ignore
from datetime import datetime, timedelta
from typing import List, Literal
from ..helpers.enums import TF_MAP, TF_MINUTES_MAP
from .handlers import BaseHandler

class Tickers(BaseHandler):
    
    def __init__(self, magic: int = -1, debug: bool = False):
        super().__init__(magic, debug)
        
    def select(self, tick: str):
        """
        Select a symbol for further processing
        """
        res = mt5.symbol_select(tick)
        return self.res(res)

    def check_connection(self):
        return mt5.terminal_info().connected

    def get_all(
        self, tickers: str | List[str] | None = None, group: str | None = None
    ):
        # Guard check, if the user provides both tickers and group
        if tickers and group:
            raise ValueError("Please provide either tickers or group, not both")

        # Fetch info for one or multiple tickers at once
        if tickers:
            if isinstance(tickers, str):
                tickers = [tickers]

            return list(map(lambda tick: mt5.symbol_info(tick)._asdict(), tickers))

        # Fetch info for all tickers, or all tickers in a group regex
        result = mt5.symbols.get() if not group else mt5.symbols_get(group=group)
        
        if result is None:
            return self.error()
        
        return self.res(list(map(lambda x: x._asdict(), result)))

    def count(self):
        """
        Get Count of all the symbols available in the terminal
        """
        return self.res(mt5.symbols_total())

    def candles(self, 
                ticker: str, 
                tf: Literal["1M", "2M", "5M", "15M", "30M", "1H", "2H", "4H", "1D", "1W", "1MN", "1Y"],  
                start_pos: int | None = None, 
                count: int | None = None,
                from_dt: datetime | None = None,
                to_dt: datetime | None = None):
        
        mt5_tf = TF_MAP[tf]
        
        if not start_pos and not count and not from_dt and not to_dt:
            raise ValueError("[Invalid Arguments]: at least 'count' is required.")
        
        if not count and not to_dt:
            raise ValueError("[Invalid Arguments]: Please provide either count or to_dt")
        
        if count and not from_dt:
            result =  mt5.copy_rates_from_pos(
                ticker, 
                mt5_tf, 
                start_pos or 1, 
                count
                )
            
            return self.res(result)
        
        if not to_dt and not from_dt:
            raise ValueError("Please provide start along with end")
        
        if not to_dt and not count:
            raise ValueError("Please provide end time or count of candles")
        
        if from_dt and not to_dt:
            start = int(from_dt.timestamp())
            result = mt5.copy_rates_from(
                ticker, 
                mt5_tf, 
                start,
                count,
                )
            return self.res(result)
        
        if from_dt and to_dt:
            _start = int(from_dt.timestamp())
            _end = int(to_dt.timestamp())
            
            result = mt5.copy_rates_range(
                ticker, 
                mt5_tf, 
                _start, 
                _end
                )
            return self.res(result)
        
        raise ValueError("Invalid Arguments")
    
    def last_candle(self, ticker: str, tf: str):
        if(tf in TF_MAP.keys()):
            mt5_tf = TF_MAP[tf]
            result =  mt5.copy_rates_from_pos(ticker, mt5_tf, 1, 1)
            return self.res(result)
        
        raise Exception("This timeframe is not supported for individual candles")
    
        # TODO: Add Custom Timeframes for getting individual candles
        # Get Latest possible bar
        count = TF_MINUTES_MAP[tf]
        now = datetime.now()
        is_below_count = now.minute < count
        minute = 59 if is_below_count else now.minute
        candle_minutes = count * int(minute / count)
        latest_bar = now.replace(minute=candle_minutes, second=0)
        
        if is_below_count:
            latest_bar = latest_bar - timedelta(hours=1)
        
        # Get minute candles to construct bars
        
    def fetch_latest(self, symbol: str):
        return mt5.symbol_info_tick(symbol)._asdict()
    
    def get_info(self, tick: str):
        return mt5.symbol_info(tick)._asdict()
    
    def trade_history(self, tick: str, from_date: datetime, to_date: datetime = datetime.now()):
        if not tick:
            raise ValueError("Please provide a valid ticker")
        
        if not from_date:
            raise ValueError("Missing: trade start date is required.")
        
        # get deals for symbols whose names contain "GBP" within a specified interval
        deals=mt5.history_deals_get(from_date, to_date, group=f"*{tick}*")
        
        if deals is None:
            return None
        
        deals = map(lambda x: x._asdict(), deals)
        deals = filter(lambda x: x["symbol"] == tick, deals)
        deals = list(deals)
        
        return self.res(deals)