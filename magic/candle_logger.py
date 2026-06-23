import os
import logging
from datetime import datetime, timezone, timedelta

from config import TICKER, BROKER_TIMEZONE

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs_live")
SYMBOL_DIR = os.path.join(LOG_DIR, TICKER)
os.makedirs(SYMBOL_DIR, exist_ok=True)


def _broker_time_converter(*args):
    """Convert log timestamps to broker timezone."""
    offset_hours = float(BROKER_TIMEZONE)
    tz = timezone(timedelta(hours=offset_hours))
    return datetime.now(tz=tz).timetuple()


def setup_live_logging():
    fmt = logging.Formatter(
        f"%(asctime)s | %(levelname)-8s | [{TICKER}] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fmt.converter = _broker_time_converter

    logger = logging.getLogger("live_engine")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.handlers.clear()

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    fh = logging.FileHandler(os.path.join(LOG_DIR, "live_engine.log"))
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger
