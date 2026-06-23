import os
from dotenv import dotenv_values
from config import TICKER

_config = dotenv_values()

MT5_ACCOUNT: int = int(_config.get("MT5_ACCOUNT", "0"))
MT5_PASSWORD: str = _config.get("MT5_PASSWORD", "")
MT5_SERVER: str = _config.get("MT5_SERVER", "")
MAGIC: int = int(_config.get("MT5_MAGIC", "10011"))

# Terminal executable path. Override in .env with MT5_PATH when using a
# different broker terminal (e.g. MetaQuotes vs Pepperstone install).
_MT5_PATH_CANDIDATES = [
    _config.get("MT5_PATH", ""),
    r"C:/Program Files/MetaTrader 5/terminal64.exe",
    r"C:/Program Files/Pepperstone MetaTrader 5/terminal64.exe",
]
MT5_PATH: str = next(
    (p for p in _MT5_PATH_CANDIDATES if p and os.path.exists(p)),
    "",
)


#accounts that require .a broker suffix
_SUFFIX_ACCOUNTS = {61485715}
def map_symbol(ticker: str) -> str:
    if MT5_ACCOUNT in _SUFFIX_ACCOUNTS and not ticker.endswith(".a"):
        return f"{ticker}.a"
    return ticker

MT5_SYMBOL = map_symbol(TICKER)
MIN_LOT = 0.01
LOT_STEP = 0.01
DEVIATION = 10

TRAINING_MONTHS = 3
LOOKBACK_DAYS = 150
