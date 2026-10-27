
"""
Screepy TicketBot — TicketMonitor: watches events for availability / price drops
"""

import time
import threading
from typing import Callable, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import requests
from loguru import logger


class EventStatus(Enum):
    UNAVAILABLE = "unavailable"
    AVAILABLE = "available"
    PRESALE = "presale"
    SOLD_OUT = "sold_out"
    PRICE_DROP = "price_drop"


@dataclass
class TicketEvent:
    """Represents a monitored ticketing event."""
    platform: str
    event_id: str
    event_name: str = ""
    venue: str = ""
    date: str = ""
    url: str = ""
    min_price: float = 0.0
    max_price: float = 0.0
    available: int = 0
    status: EventStatus = EventStatus.UNAVAILABLE
    last_checked: Optional[datetime] = None
    price_history: list = field(default_factory=list)


class TicketMonitor:
    """
    Continuously monitors ticketing platforms for changes in ticket
    availability, price drops, and presale openings.
    Fires callbacks when significant changes are detected.
    """

    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval
        self._events: List[TicketEvent] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable] = []
        self._lock = threading.Lock()

    def add_event(self, platform: str, event_id: str, url: str = "") -> TicketEvent:
        """Register an event for monitoring."""
        event = TicketEvent(
            platform=platform,
            event_id=event_id,
            url=url or f"https://www.{platform}.com/event/{event_id}",
        )
        with self._lock:
            self._events.append(event)
        logger.info(f"Now monitoring {platform}/{event_id}")
        return event

    def remove_event(self, platform: str, event_id: str) -> bool:
        """Stop monitoring an event."""
        with self._lock:
            before = len(self._events)
            self._events = [
                e for e in self._events
                if not (e.platform == platform and e.event_id == event_id)
            ]
            return len(self._events) < before

    def on_change(self, callback: Callable):
        """Register a callback fired when an event status changes."""
        self._callbacks.append(callback)

    def _check_event(self, event: TicketEvent) -> Optional[TicketEvent]:
        """
        Query a platform for the current state of an event.
        (Placeholder — real implementation calls platform APIs.)
        """
        from bots.utils import safe_request
        headers = {"User-Agent": "ScreepyTicketBot/1.0"}
        try:
            resp = safe_request(event.url, headers=headers, timeout=15)
            if resp and resp.status_code == 200:
                # Simulate parsing — real logic would use BeautifulSoup / API
                old_status = event.status
                event.status = EventStatus.AVAILABLE
                event.last_checked = datetime.now()
                event.available = 42  # placeholder
                event.min_price = 89.50
                event.max_price = 249.00
                event.price_history.append((time.time(), event.min_price))

                if old_status != event.status:
                    logger.info(f"[{event.event_id}] Status changed: {old_status} → {event.status}")
                    for cb in self._callbacks:
                        cb(event)
                return event
        except Exception as exc:
            logger.warning(f"Check failed for {event.event_id}: {exc}")
        return None

    def start(self):
        """Start the monitoring loop in a background thread."""
        if self._running:
            logger.warning("Monitor already running.")
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info(f"Monitoring started (interval={self.check_interval}s)")

    def stop(self):
        """Stop the monitoring loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("Monitoring stopped.")

    def _loop(self):
        """Main monitoring loop."""
        while self._running:
            with self._lock:
                events_snapshot = list(self._events)
            for event in events_snapshot:
                self._check_event(event)
            time.sleep(self.check_interval)

    def get_events(self) -> List[TicketEvent]:
        """Return a snapshot of all monitored events."""
        with self._lock:
            return list(self._events)
