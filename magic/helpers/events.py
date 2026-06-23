import logging
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger("live_engine")


class Events(Enum):
    FETCH_DONE = "FETCH_DONE"
    SIG_LONG_ENTRY = "SIG_LONG_ENTRY"
    SIG_SHORT_ENTRY = "SIG_SHORT_ENTRY"
    SIG_LONG_EXIT = "SIG_LONG_EXIT"
    SIG_SHORT_EXIT = "SIG_SHORT_EXIT"


class EventBus:
    """Synchronous in-process pub/sub bus.

    Subscribers are called sequentially in publish order, which guarantees
    that exit checks run before entry checks when both are subscribed to
    the same event (FETCH_DONE).
    """

    def __init__(self):
        self._subscribers: dict[Events, list[Callable]] = {}

    def subscribe(self, event_type: Events, callback: Callable) -> None:
        self._subscribers.setdefault(event_type, []).append(callback)

    def publish(self, event_type: Events, data: dict[str, Any] | None = None) -> None:
        handlers = self._subscribers.get(event_type, [])
        if not handlers:
            return
        # Log entry signals and exit signals at INFO; FETCH_DONE at DEBUG
        # to avoid flooding the log every 8 min with FETCH_DONE
        if event_type != Events.FETCH_DONE:
            detail = ""
            if data:
                if "reason" in data:
                    detail = f" reason={data['reason']}"
                elif "bar_ts" in data:
                    detail = f" bar={data['bar_ts']}"
            logger.info(f"[EVENT] {event_type.value}{detail} -> {len(handlers)} handlers")

        for cb in handlers:
            try:
                cb(data or {})
            except Exception as e:
                logger.error(
                    f"[EVENT] {event_type.value} handler {cb.__name__} failed: {e}",
                    exc_info=True,
                )
