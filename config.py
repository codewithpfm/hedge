from pathlib import Path

from dotenv import dotenv_values

config = dotenv_values()

_REPO_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = _REPO_ROOT / "runs"


FEES = 5 #flexible
LEVERAGE = 10 #flexible
CASH = 100000 #flexible
TICKER = "XAUUSD" #flexible
STARTDATE = "2025-04-19" #flexible format YYYY-MM-DD
ENDDATE = "2026-02-19" #flexible (Polygon marks the last few days DELAYED)

ENTRY_DELAY_MINS     = 30 #delay entry by this many minutes (>= VWAP_TF_MINS so the first session VWAP bar has closed).
VWAP_TF_MINS         = 30 #VWAP timeframe in minutes.
MAX_HOLD_HOURS       = 23 #force-close any leg held longer than this
RISK_PERCENT         = 0.3 #fraction of free balance risked per leg (ATR-based sizing)
# Per-symbol ATR-min thresholds
# ATR is denominated in the instrument's own price units
ATR_MIN_THRESHOLD = {
    "EURUSD": 0.0030,
    "GBPUSD": 0.0040,
    "XAUUSD": 10,
    "USOIL":  0.60,
}

POLYGON_API_KEY = config.get("POLYGON_API_KEY", "")
DATA_BASE_URL = "https://api.massive.com/v2/aggs/ticker"
BROKER_TIMEZONE = "3"  # GMT+3 (common forex broker server time)

# Trading session that anchors the VWAP reset. One of: "london", "newyork",
# "tokyo", "sydney", "utc" (see utils/maps.py).

SESSION = "newyork"  # flexible

# Logging
LOG_DIR = ".logs/nautilus"
LOG_LEVEL = "INFO"

