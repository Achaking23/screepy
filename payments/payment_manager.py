
"""
Screepy TicketBot — PaymentManager: handles payment processing & card management
"""

import json
import time
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass, field, asdict

from loguru import logger
from bots.utils import obfuscate_card


@dataclass
class PaymentCard:
    """Represents a payment card."""
    nickname: str
    card_number: str
    expiry_month: str
    expiry_year: str
    cvv: str
    cardholder_name: str
    billing_zip: str = ""
    brand: str = ""  # visa, mastercard, amex, discover
    active: bool = True
    use_count: int = 0
    last_used: float = 0.0


@dataclass
class PaymentResult:
    """Result of a payment attempt."""
    success: bool
    transaction_id: str = ""
    amount: float = 0.0
    card_used: str = ""
    error: Optional[str] = None
    timestamp: float = 0.0


class PaymentManager:
    """
    Manages payment methods, processes transactions, and handles
    retries on failure. Supports multiple card profiles and
    virtual card generation.
    """

    def __init__(self, storage_dir: str = "payments/cards"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._cards: List[PaymentCard] = []
        self._load()

    def _load(self):
        """Load saved cards from disk."""
        cards_file = self.storage_dir / "cards.json"
        if cards_file.exists():
            try:
                with open(cards_file, "r") as f:
                    data = json.load(f)
                self._cards = [PaymentCard(**item) for item in data]
                logger.info(f"Loaded {len(self._cards)} payment card(s).")
            except Exception as exc:
                logger.warning(f"Could not load cards: {exc}")

    def _save(self):
        """Persist cards to disk."""
        cards_file = self.storage_dir / "cards.json"
        data = [asdict(c) for c in self._cards]
        with open(cards_file, "w") as f:
            json.dump(data, f, indent=2)
        logger.debug(f"Saved {len(self._cards)} card(s).")

    def add_card(self, card: PaymentCard):
        """Add a new card to the manager."""
        self._cards.append(card)
        self._save()
        logger.info(f"Card added: {card.nickname} ({obfuscate_card(card.card_number)})")

    def remove_card(self, nickname: str) -> bool:
        """Remove a card by nickname."""
        before = len(self._cards)
        self._cards = [c for c in self._cards if c.nickname != nickname]
        if len(self._cards) < before:
            self._save()
            logger.info(f"Card '{nickname}' removed.")
            return True
        return False

    def get_active_cards(self) -> List[PaymentCard]:
        """Return all non-banned cards."""
        return [c for c in self._cards if c.active]

    def process_payment(
        self,
        card: PaymentCard,
        amount: float,
        merchant: str = "",
        retries: int = 3,
    ) -> PaymentResult:
        """
        Process a payment transaction.
        (Placeholder — integrates with a payment gateway.)
        """
        for attempt in range(1, retries + 1):
            try:
                logger.info(
                    f"Processing ${amount:.2f} payment with {card.nickname} "
                    f"(attempt {attempt}/{retries})..."
                )
                # Simulated payment processing
                time.sleep(1.5)

                # Simulate success
                import random
                txn_id = f"TXN-{random.randint(100000000, 999999999)}"
                card.use_count += 1
                card.last_used = time.time()

                result = PaymentResult(
                    success=True,
                    transaction_id=txn_id,
                    amount=amount,
                    card_used=obfuscate_card(card.card_number),
                    timestamp=time.time(),
                )
                logger.success(f"Payment successful: {txn_id} (${amount:.2f})")
                self._save()
                return result

            except Exception as exc:
                logger.error(f"Payment attempt {attempt} failed: {exc}")
                if attempt < retries:
                    time.sleep(2 ** attempt)

        return PaymentResult(
            success=False,
            amount=amount,
            card_used=obfuscate_card(card.card_number),
            error="All payment attempts failed",
            timestamp=time.time(),
        )

    def get_stats(self) -> dict:
        """Return payment manager statistics."""
        active = self.get_active_cards()
        total_uses = sum(c.use_count for c in self._cards)
        return {
            "total_cards": len(self._cards),
            "active_cards": len(active),
            "total_uses": total_uses,
        }
