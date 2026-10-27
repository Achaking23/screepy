
"""
Screepy TicketBot — BotManager: orchestrates multiple MiniBot instances
"""

import time
import threading
import uuid
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from loguru import logger

from .mini_bot import MiniBot, BotSession, BotStatus, Platform
from .utils import load_config


class BotManager:
    """
    Manages a pool of MiniBot workers to acquire tickets in parallel.
    Handles session creation, proxy assignment, rate limiting, and
    result aggregation.
    """

    def __init__(self, config_path: str = "config/settings.yaml"):
        self.config = load_config(config_path)
        self.sessions: List[BotSession] = []
        self.results: List[dict] = []
        self._lock = threading.Lock()
        self._active_count = 0
        self._max_concurrent = 5  # configurable

    def create_session(
        self,
        platform: Platform,
        event_id: str,
        account: Optional[dict] = None,
        proxy: Optional[str] = None,
    ) -> BotSession:
        """Create a new bot session."""
        session = BotSession(
            bot_id=f"bot-{uuid.uuid4().hex[:8]}",
            platform=platform,
            event_id=event_id,
            account=account,
            proxy=proxy,
        )
        with self._lock:
            self.sessions.append(session)
        logger.info(f"Session created: {session.bot_id} ({platform.value}/{event_id})")
        return session

    def _worker(self, session: BotSession) -> dict:
        """Run a single MiniBot and return its result."""
        bot = None
        try:
            bot = MiniBot(session, self.config)
            with self._lock:
                self._active_count += 1
            result = bot.run()
            return result
        except Exception as exc:
            logger.error(f"[{session.bot_id}] Worker crashed: {exc}")
            return {
                "bot_id": session.bot_id,
                "status": "failed",
                "error": str(exc),
            }
        finally:
            if bot:
                bot.cleanup()
            with self._lock:
                self._active_count -= 1

    def launch_all(self, max_workers: int = 5) -> List[dict]:
        """
        Launch all pending sessions concurrently.
        Returns a list of result dicts.
        """
        pending = [s for s in self.sessions if s.status == BotStatus.IDLE]
        if not pending:
            logger.warning("No pending sessions to launch.")
            return []

        logger.info(f"Launching {len(pending)} bot(s) with {max_workers} worker(s)...")
        self.results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {executor.submit(self._worker, s): s for s in pending}
            for future in as_completed(future_map):
                result = future.result()
                with self._lock:
                    self.results.append(result)
                logger.info(f"Bot {result.get('bot_id')} finished: {result.get('status')}")

        return self.results

    def launch_single(self, session: BotSession) -> dict:
        """Launch a single bot session synchronously."""
        return self._worker(session)

    def get_active_count(self) -> int:
        """Return the number of currently running bots."""
        with self._lock:
            return self._active_count

    def get_summary(self) -> dict:
        """Return a summary of all sessions."""
        with self._lock:
            total = len(self.sessions)
            succeeded = sum(
                1 for s in self.sessions if s.status == BotStatus.SUCCESS
            )
            failed = sum(
                1 for s in self.sessions if s.status == BotStatus.FAILED
            )
            captcha = sum(
                1 for s in self.sessions if s.status == BotStatus.CAPTCHA
            )
            banned = sum(
                1 for s in self.sessions if s.status == BotStatus.BANNED
            )
        return {
            "total": total,
            "succeeded": succeeded,
            "failed": failed,
            "captcha_blocked": captcha,
            "banned": banned,
            "active": self._active_count,
        }

    def reset(self):
        """Clear all sessions and results."""
        with self._lock:
            self.sessions.clear()
            self.results.clear()
            self._active_count = 0
        logger.info("BotManager reset.")
