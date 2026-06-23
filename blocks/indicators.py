class Indicators:
    
    def __init__(self, data, indicators: dict[str, list[int]] | None = None):
        self.data = data
        
        if indicators is not None:
            self.df = self.get_indicators(indicators)
        
    def get_indicators(self, indicators: dict[str, list[int]]):
        df = self.data.copy()
        
        for indicator, values in indicators.items():
            for span in values:
                if indicator == "EMA":
                    df[f"{indicator}_{span}"] = df["Close"].ewm(span=span, adjust=False).mean()
                    
                elif indicator == "VWMA":
                    df[f"{indicator}_{span}"] = self._vwma(df["Close"], df["Volume"], span)
                
                elif indicator == "VWAP":
                    df[f"{indicator}_{span}"] = self._vwap(df["High"], df["Low"], 
                                                           df["Close"], df["Volume"], span)
                else: 
                    raise Exception("Indicator not supported", indicator, span)
                
        return df
    
    def _vwma(self, close, volume, length):
        """Volume Weighted Moving Average"""
        pv = close * volume
        return pv.rolling(window=length).sum() / volume.rolling(window=length).sum()
    
    def _vwap(self, high, low, close, volume, length):
        """Volume Weighted Average Price"""
        typical_price = (high + low + close) / 3
        pv = typical_price * volume
        return pv.rolling(window=length).sum() / volume.rolling(window=length).sum()