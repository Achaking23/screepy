
"""
Screepy TicketBot — TicketAcquirer: high-level orchestrator for purchasing tickets
"""

from typing import Optional, List
from dataclasses import dataclass, field

from loguru import logger

from bots.bot_manager import BotManager
from bots.mini_bot import Platform, BotStatus
from accounts.account_manager import AccountManager


@dataclass
class AcquisitionPlan:
    """Parameters for a ticket acquisition operation."""
    platform: Platform
    event_id: str
    quantity: int = 2
    max_price: float = 0.0  # 0 = no limit
    bots_count: int = 3
    presale: bool = False
    proxy_required: bool = False
    account_email: Optional[str] = None
    account_password: Optional[str] = None


@dataclass
class AcquisitionResult:
    """Outcome of an acquisition attempt."""
    success: bool
    platform: str
    event_id: str
    tickets_acquired: int = 0
    total_paid: float = 0.0
    confirmation_code: str = ""
    error: Optional[str] = None
    bot_results: list = field(default_factory=list)


class TicketAcquirer:
    """
    Coordinates the end-to-end ticket purchase flow:
      1. Prepare accounts & proxies
      2. Launch parallel bot sessions
      3. Handle rate limiting & retries
      4. Collect results
    """

    def __init__(
        self,
        bot_manager: Optional[BotManager] = None,
        account_manager: Optional[AccountManager] = None,
    ):
        self.bot_manager = bot_manager or BotManager()
        self.account_manager = account_manager or AccountManager()

    def acquire(self, plan: AcquisitionPlan) -> AcquisitionResult:
        """
        Execute a full acquisition plan.
        Returns the aggregated result.
        """
        logger.info(
            f"Starting acquisition: {plan.quantity}x {plan.event_id} "
            f"on {plan.platform.value} ({plan.bots_count} bot(s))"
        )

        # 1. Create bot sessions
        sessions = []
        for i in range(plan.bots_count):
            account = None
            if plan.account_email:
                account = {
                    "email": plan.account_email,
                    "password": plan.account_password or "",
                }
            session = self.bot_manager.create_session(
                platform=plan.platform,
                event_id=plan.event_id,
                account=account,
            )
            sessions.append(session)

        # 2. Launch all bots
        results = self.bot_manager.launch_all(max_workers=plan.bots_count)

        # 3. Aggregate results
        successes = [r for r in results if r.get("status") == "success"]
        failures = [r for r in results if r.get("status") == "failed"]

        if successes:
            first_success = successes[0]
            result = AcquisitionResult(
                success=True,
                platform=plan.platform.value,
                event_id=plan.event_id,
                tickets_acquired=first_success.get("result", {}).get("tickets", 0),
                total_paid=first_success.get("result", {}).get("total", 0.0),
                confirmation_code=first_success.get("result", {}).get("confirmation", ""),
                bot_results=results,
            )
            logger.success(f"Acquired {result.tickets_acquired} ticket(s) for {plan.event_id}!")
        else:
            result = AcquisitionResult(
                success=False,
                platform=plan.platform.value,
                event_id=plan.event_id,
                error=f"All {len(failures)} bot(s) failed",
                bot_results=results,
            )
            logger.error(f"Acquisition failed: {result.error}")

        return result

    def rapid_acquire(
        self,
        platform: str,
        event_id: str,
        quantity: int = 2,
        bots: int = 5,
    ) -> AcquisitionResult:
        """
        Convenience method for a quick acquisition with sensible defaults.
        """
        plat_map = {
            "ticketmaster": Platform.TICKETMASTER,
            "axs": Platform.AXS,
            "seatgeek": Platform.SEATGEEK,
            "stubhub": Platform.STUBHUB,
            "vividseats": Platform.VIVIDSEATS,
        }
        platform_enum = plat_map.get(platform.lower())
        if not platform_enum:
            raise ValueError(f"Unsupported platform: {platform}")

        plan = AcquisitionPlan(
            platform=platform_enum,
            event_id=event_id,
            quantity=quantity,
            bots_count=bots,
        )
        return self.acquire(plan)
