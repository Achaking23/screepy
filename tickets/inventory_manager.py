
"""
Screepy TicketBot — InventoryManager: tracks ticket inventory & pricing
"""

import json
import time
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass, field, asdict

from loguru import logger


@dataclass
class TicketListing:
    """A single ticket listing from any platform."""
    platform: str
    event_id: str
    section: str = ""
    row: str = ""
    seat: str = ""
    price: float = 0.0
    quantity: int = 1
    listing_url: str = ""
    seller_rating: float = 0.0
    timestamp: float = 0.0


@dataclass
class EventInventory:
    """Full inventory snapshot for an event at a point in time."""
    platform: str
    event_id: str
    event_name: str = ""
    listings: List[TicketListing] = field(default_factory=list)
    min_price: float = 0.0
    max_price: float = 0.0
    total_available: int = 0
    captured_at: float = 0.0


class InventoryManager:
    """
    Stores, queries, and exports ticket inventory data.
    Maintains historical snapshots for price-trend analysis.
    """

    def __init__(self, storage_dir: str = "tickets/inventory_data"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict = {}  # (platform, event_id) -> EventInventory

    def store_snapshot(self, inventory: EventInventory):
        """Save an inventory snapshot to disk and update the cache."""
        timestamp = int(time.time())
        filename = f"{inventory.platform}_{inventory.event_id}_{timestamp}.json"
        filepath = self.storage_dir / filename

        data = asdict(inventory)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
        self._cache[(inventory.platform, inventory.event_id)] = inventory
        logger.info(
            f"Inventory saved: {inventory.total_available} ticket(s) "
            f"for {inventory.event_id} (${inventory.min_price:.2f} – ${inventory.max_price:.2f})"
        )

    def load_snapshots(
        self,
        platform: str,
        event_id: str,
        limit: int = 10,
    ) -> List[EventInventory]:
        """Load the most recent inventory snapshots for an event."""
        pattern = f"{platform}_{event_id}_*.json"
        files = sorted(self.storage_dir.glob(pattern), reverse=True)[:limit]
        snapshots = []
        for fpath in files:
            with open(fpath, "r") as f:
                data = json.load(f)
                snapshots.append(EventInventory(**data))
        return snapshots

    def get_best_deal(
        self,
        platform: str,
        event_id: str,
        max_price: float = 0.0,
        quantity: int = 2,
    ) -> Optional[TicketListing]:
        """Find the cheapest available listing meeting criteria."""
        snapshot = self._cache.get((platform, event_id))
        if not snapshot:
            return None

        candidates = [
            l for l in snapshot.listings
            if l.quantity >= quantity and (max_price == 0 or l.price <= max_price)
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda l: l.price)

    def price_trend(self, platform: str, event_id: str, hours: int = 24) -> dict:
        """Get min/avg/max price trend over the last N hours."""
        snapshots = self.load_snapshots(platform, event_id, limit=100)
        cutoff = time.time() - (hours * 3600)
        recent = [s for s in snapshots if s.captured_at >= cutoff]

        if not recent:
            return {"min": 0, "avg": 0, "max": 0, "data_points": 0}

        prices = [s.min_price for s in recent if s.min_price > 0]
        return {
            "min": min(prices) if prices else 0,
            "avg": sum(prices) / len(prices) if prices else 0,
            "max": max(prices) if prices else 0,
            "data_points": len(recent),
        }

    def clear_cache(self):
        """Clear the in-memory cache."""
        self._cache.clear()
        logger.debug("Inventory cache cleared.")
