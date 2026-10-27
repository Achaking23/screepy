
"""
Screepy TicketBot — ProxyManager: manages proxy rotation, health checks, and bans
"""

import time
import threading
import random
from pathlib import Path
from typing import Optional, List, Tuple
from dataclasses import dataclass, field

import requests
from loguru import logger


@dataclass
class Proxy:
    """A single proxy endpoint."""
    address: str
    protocol: str = "http"   # http, https, socks4, socks5
    port: int = 0
    username: Optional[str] = None
    password: Optional[str] = None
    country: str = ""
    latency_ms: float = 0.0
    alive: bool = True
    ban_count: int = 0
    ban_threshold: int = 5
    last_checked: float = 0.0
    last_used: float = 0.0

    def url(self) -> str:
        """Return the proxy URL for requests."""
        auth = ""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        return f"{self.protocol}://{auth}{self.address}:{self.port}"

    def to_dict(self) -> dict:
        """Return requests-compatible proxy dict."""
        return {
            "http": self.url(),
            "https": self.url(),
        }


class ProxyManager:
    """
    Manages a pool of proxies with automatic health checks,
    rotation, and ban detection.
    """

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self._proxies: List[Proxy] = []
        self._lock = threading.Lock()
        self._running = False
        self._check_url = self.config.get("check_url", "https://api.ipify.org")
        self._ban_threshold = self.config.get("ban_threshold", 5)
        self._load_from_file()

    def _load_from_file(self):
        """Load proxies from a text file (one proxy per line)."""
        source = self.config.get("source_file", "proxies/list.txt")
        path = Path(source)
        if path.exists():
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        self.add_proxy(Proxy(address=line))
            logger.info(f"Loaded {len(self._proxies)} proxy(ies) from {source}")
        else:
            logger.info(f"No proxy file at {source}; starting with empty pool.")

    def add_proxy(self, proxy: Proxy):
        """Add a proxy to the pool."""
        with self._lock:
            self._proxies.append(proxy)

    def remove_proxy(self, address: str) -> bool:
        """Remove a proxy by address."""
        with self._lock:
            before = len(self._proxies)
            self._proxies = [p for p in self._proxies if p.address != address]
            return len(self._proxies) < before

    def get_working_proxy(self) -> Optional[Proxy]:
        """
        Return a random alive proxy with lowest latency, or None.
        """
        with self._lock:
            alive = [p for p in self._proxies if p.alive and p.ban_count < self._ban_threshold]
            if not alive:
                logger.warning("No working proxies available!")
                return None
            # Prefer lower latency
            alive.sort(key=lambda p: p.latency_ms)
            # Pick from top 3 randomly
            return random.choice(alive[:min(3, len(alive))])

    def check_proxy(self, proxy: Proxy) -> bool:
        """
        Test whether a proxy is alive by connecting to a check URL.
        Returns True if working.
        """
        try:
            start = time.time()
            resp = requests.get(
                self._check_url,
                proxies=proxy.to_dict(),
                timeout=10,
            )
            latency = (time.time() - start) * 1000
            proxy.latency_ms = latency
            proxy.last_checked = time.time()

            if resp.status_code == 200:
                proxy.alive = True
                logger.debug(f"Proxy {proxy.address} OK ({latency:.0f}ms)")
                return True
            else:
                proxy.alive = False
                return False
        except Exception:
            proxy.alive = False
            return False

    def mark_banned(self, address: str):
        """Increment ban counter for a proxy."""
        with self._lock:
            for p in self._proxies:
                if p.address == address:
                    p.ban_count += 1
                    p.alive = p.ban_count < self._ban_threshold
                    if not p.alive:
                        logger.warning(f"Proxy {address} deactivated (banned).")
                    break

    def health_check_all(self):
        """Test all proxies in the pool."""
        with self._lock:
            proxies = list(self._proxies)
        for proxy in proxies:
            self.check_proxy(proxy)
        alive_count = sum(1 for p in proxies if p.alive)
        logger.info(f"Health check complete: {alive_count}/{len(proxies)} alive")

    def start_auto_health_check(self, interval: int = 120):
        """Start background health-check thread."""
        if self._running:
            return

        def loop():
            while self._running:
                self.health_check_all()
                time.sleep(interval)

        self._running = True
        thread = threading.Thread(target=loop, daemon=True)
        thread.start()
        logger.info(f"Auto health-check started (interval={interval}s)")

    def stop_auto_health_check(self):
        """Stop the background health-check thread."""
        self._running = False
        logger.info("Auto health-check stopped.")

    def get_stats(self) -> dict:
        """Return proxy pool statistics."""
        with self._lock:
            total = len(self._proxies)
            alive = sum(1 for p in self._proxies if p.alive)
            banned = sum(1 for p in self._proxies if p.ban_count >= self._ban_threshold)
        return {
            "total": total,
            "alive": alive,
            "banned": banned,
            "dead": total - alive - banned,
        }
