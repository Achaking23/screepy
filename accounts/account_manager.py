
"""
Screepy TicketBot — AccountManager: manages platform account lifecycle
"""

import json
import time
import threading
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass, field, asdict

from loguru import logger

from .email_generator import EmailGenerator, EmailAccount


@dataclass
class PlatformAccount:
    """A registered account on a ticketing platform."""
    email: str
    password: str
    platform: str
    user_id: Optional[str] = None
    verified: bool = False
    cookies: dict = field(default_factory=dict)
    created_at: float = 0.0
    last_used: float = 0.0
    use_count: int = 0
    banned: bool = False


class AccountManager:
    """
    Manages a pool of platform accounts: creation, verification,
    cooldown tracking, and persistence to disk.
    """

    def __init__(self, storage_dir: str = "accounts/store"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._accounts: List[PlatformAccount] = []
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        """Load persisted accounts from disk."""
        store_file = self.storage_dir / "accounts.json"
        if store_file.exists():
            try:
                with open(store_file, "r") as f:
                    data = json.load(f)
                with self._lock:
                    for item in data:
                        self._accounts.append(PlatformAccount(**item))
                logger.info(f"Loaded {len(data)} account(s) from disk.")
            except Exception as exc:
                logger.warning(f"Could not load accounts: {exc}")

    def _save(self):
        """Persist all accounts to disk."""
        store_file = self.storage_dir / "accounts.json"
        with self._lock:
            data = [asdict(a) for a in self._accounts]
        with open(store_file, "w") as f:
            json.dump(data, f, indent=2, default=str)
        logger.debug(f"Saved {len(data)} account(s) to disk.")

    def create_accounts(
        self,
        platform: str,
        count: int = 1,
        domain: Optional[str] = None,
    ) -> List[PlatformAccount]:
        """Generate and register new accounts for a platform."""
        generator = EmailGenerator(domain=domain)
        emails = generator.generate_bulk(count)

        created = []
        for email_account in emails:
            account = PlatformAccount(
                email=email_account.email,
                password=email_account.password,
                platform=platform,
                created_at=time.time(),
            )
            with self._lock:
                self._accounts.append(account)
            created.append(account)
            logger.info(f"Created account {account.email} for {platform}")

        self._save()
        return created

    def get_available(self, platform: str) -> Optional[PlatformAccount]:
        """
        Return the next available (non-banned, non-cooldown) account
        for a given platform, or None.
        """
        now = time.time()
        with self._lock:
            for acc in self._accounts:
                if acc.platform == platform and not acc.banned:
                    if now - acc.last_used > 3600:  # 1-hour cooldown
                        acc.last_used = now
                        acc.use_count += 1
                        return acc
        return None

    def mark_banned(self, email: str):
        """Mark an account as banned."""
        with self._lock:
            for acc in self._accounts:
                if acc.email == email:
                    acc.banned = True
                    logger.warning(f"Account {email} marked as BANNED.")
                    break
        self._save()

    def mark_verified(self, email: str, user_id: str = ""):
        """Mark an account as email-verified."""
        with self._lock:
            for acc in self._accounts:
                if acc.email == email:
                    acc.verified = True
                    acc.user_id = user_id or acc.user_id
                    break
        self._save()

    def total_count(self, platform: Optional[str] = None) -> int:
        """Return total number of accounts, optionally filtered by platform."""
        with self._lock:
            if platform:
                return sum(1 for a in self._accounts if a.platform == platform)
            return len(self._accounts)

    def banned_count(self, platform: Optional[str] = None) -> int:
        """Return count of banned accounts."""
        with self._lock:
            if platform:
                return sum(1 for a in self._accounts if a.platform == platform and a.banned)
            return sum(1 for a in self._accounts if a.banned)

    def get_stats(self) -> dict:
        """Return account pool statistics."""
        with self._lock:
            return {
                "total": len(self._accounts),
                "banned": sum(1 for a in self._accounts if a.banned),
                "verified": sum(1 for a in self._accounts if a.verified),
                "platforms": list(set(a.platform for a in self._accounts)),
            }

    def save_cookies(self, email: str, cookies: dict):
        """Save session cookies for an account."""
        with self._lock:
            for acc in self._accounts:
                if acc.email == email:
                    acc.cookies = cookies
                    break
        self._save()
