"""
Screepy TicketBot — Utility functions for bots
"""

import json
import time
import random
import hashlib
from pathlib import Path
from typing import Optional

import requests
from loguru import logger


def load_config(path: str = "config/settings.yaml") -> dict:
    """Load YAML configuration file."""
    from ruamel.yaml import YAML
    with open(path, "r", encoding="utf-8") as f:
        return YAML(typ='safe').load(f)


def user_agent_rotator() -> str:
    """Return a random desktop User-Agent string."""
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    ]
    return random.choice(agents)


def random_delay(min_s: float = 0.5, max_s: float = 2.0) -> None:
    """Sleep for a random interval to mimic human behaviour."""
    delay = random.uniform(min_s, max_s)
    logger.debug(f"Delaying {delay:.2f}s")
    time.sleep(delay)


def fingerprint(platform: str, event_id: str, account: str) -> str:
    """Generate a unique fingerprint string for a session."""
    raw = f"{platform}:{event_id}:{account}:{time.time()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def safe_request(
    url: str,
    method: str = "GET",
    headers: Optional[dict] = None,
    proxies: Optional[dict] = None,
    timeout: int = 30,
    retries: int = 3,
) -> Optional[requests.Response]:
    """Make an HTTP request with retry logic."""
    for attempt in range(1, retries + 1):
        try:
            resp = requests.request(
                method=method,
                url=url,
                headers=headers or {},
                proxies=proxies,
                timeout=timeout,
            )
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            logger.warning(f"Request failed (attempt {attempt}/{retries}): {exc}")
            if attempt < retries:
                time.sleep(2 ** attempt)
    return None


def parse_price(text: str) -> float:
    """Extract a float price from a string like "$49.50" or "€120,00"."""
    cleaned = text.replace("$", "").replace("€", "").replace(",", ".").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def obfuscate_card(card_number: str) -> str:
    """Return masked card number showing only last 4 digits."""
    return f"**** **** **** {card_number[-4:]}" if len(card_number) >= 4 else "****"


def ensure_dir(path: str) -> Path:
    """Ensure a directory exists and return the Path object."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p
