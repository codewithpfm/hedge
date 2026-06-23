"""Lookup tables and helpers for broker timezones and trading sessions."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytz

# ── Broker-timezone map ───────────────────────────────────────────────────
# Maps the BROKER_TIMEZONE config value (a GMT-offset string) to the timezone
# the MT5 broker connection runs on.
tz_map = {
  '0': pytz.utc,
  '1': 'Etc/GMT-1',
  '2': 'Etc/GMT-2',
  '3': 'Etc/GMT-3',
  '4': 'Etc/GMT-4',
  '5': 'Etc/GMT-5',
  '5:30': 'Asia/Kolkata',
  '6': 'Etc/GMT-6',
  '7': 'Etc/GMT-7',
  '8': 'Etc/GMT-8',
  '9': 'Etc/GMT-9',
  '10': 'Etc/GMT-10',
  '11': 'Etc/GMT-11',
  '12': 'Etc/GMT-12',
  '-1': 'Etc/GMT+1',
  '-2': 'Etc/GMT+2',
  '-3': 'Etc/GMT+3',
  '-4': 'Etc/GMT+4',
  '-5': 'Etc/GMT+5',
  '-6': 'Etc/GMT+6',
  '-7': 'Etc/GMT+7',
  '-8': 'Etc/GMT+8',
  '-9': 'Etc/GMT+9',
  '-10': 'Etc/GMT+10',
  '-11': 'Etc/GMT+11',
  '-12': 'Etc/GMT+12',
  'IN/Kolkata': 'Asia/Kolkata',
}


# ── Trading sessions ──────────────────────────────────────────────────────
# Session open / close hours expressed in UTC. ``close`` is informational
# only; the VWAP reset is anchored to ``open``. "utc" preserves the legacy
# behaviour of resetting on the UTC calendar day (open hour 0).
SESSION_HOURS: dict[str, dict[str, int]] = {
    "sydney": {"open": 21, "close": 6},
    "tokyo": {"open": 0, "close": 9},
    "london": {"open": 7, "close": 16},
    "newyork": {"open": 12, "close": 21},
    "utc": {"open": 0, "close": 0},
}

DEFAULT_SESSION = "utc"


def normalize(session: str | None) -> str:
    """Lower-case / validate a session name, falling back to the default."""
    key = (session or DEFAULT_SESSION).strip().lower()
    if key not in SESSION_HOURS:
        raise ValueError(
            f"Unknown session {session!r}. "
            f"Choose one of: {', '.join(sorted(SESSION_HOURS))}"
        )
    return key


def session_open_hour(session: str | None) -> int:
    """UTC hour at which the given session opens (and the VWAP resets)."""
    return SESSION_HOURS[normalize(session)]["open"]


def session_bucket(ts_utc: datetime, session: str | None) -> date:
    """Calendar date of the session that ``ts_utc`` (UTC) belongs to.

    Shifting the timestamp back by the session open hour makes ``.date()``
    advance exactly at the session open, so a change in the returned value
    marks a new session and triggers the VWAP reset.
    """
    return (ts_utc - timedelta(hours=session_open_hour(session))).date()
