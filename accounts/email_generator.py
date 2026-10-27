
"""
Screepy TicketBot — Email generator for disposable account creation
"""

import random
import string
import time
from typing import Optional
from dataclasses import dataclass

from loguru import logger


@dataclass
class EmailAccount:
    """Represents a generated disposable email account."""
    email: str
    username: str
    domain: str
    password: str
    created_at: float = 0.0


class EmailGenerator:
    """
    Generates disposable email addresses for mass account registration
    on ticketing platforms. Supports custom domains, prefix patterns,
    and optional password generation.
    """

    COMMON_DOMAINS = [
        "tempmail.com",
        "10minute.net",
        "guerrillamail.com",
        "mailnator.com",
        "throwaway.io",
        "yopmail.com",
        "emailondeck.com",
        "tmail.com",
        "spambox.us",
        "maildrop.cc",
    ]

    ADJECTIVES = [
        "swift", "rapid", "quick", "fast", "bold", "eager", "keen",
        "sharp", "smart", "agile", "lucky", "super", "ultra", "mega",
    ]

    NOUNS = [
        "tiger", "hawk", "wolf", "falcon", "puma", "viper", "shark",
        "fox", "lion", "eagle", "panther", "cheetah", "phoenix",
    ]

    def __init__(
        self,
        domain: Optional[str] = None,
        password_length: int = 16,
        include_symbols: bool = True,
    ):
        self.domain = domain or random.choice(self.COMMON_DOMAINS)
        self.password_length = password_length
        self.include_symbols = include_symbols

    def _generate_username(self, prefix: str = "tix") -> str:
        """Generate a human-like username."""
        style = random.choice(["word", "mixed", "random"])

        if style == "word":
            adj = random.choice(self.ADJECTIVES)
            noun = random.choice(self.NOUNS)
            num = random.randint(10, 9999)
            return f"{adj}{noun}{num}"
        elif style == "mixed":
            return f"{prefix}{random.randint(10000, 99999)}{random.choice(string.ascii_lowercase)}"
        else:
            length = random.randint(8, 14)
            return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

    def _generate_password(self) -> str:
        """Generate a strong random password."""
        chars = string.ascii_letters + string.digits
        if self.include_symbols:
            chars += "!@#$%^&*"
        return ''.join(random.choices(chars, k=self.password_length))

    def generate(self, prefix: str = "tix", count: int = 1) -> list:
        """Generate one or more disposable email accounts."""
        accounts = []
        for _ in range(count):
            username = self._generate_username(prefix)
            email = f"{username}@{self.domain}"
            password = self._generate_password()
            accounts.append(EmailAccount(
                email=email,
                username=username,
                domain=self.domain,
                password=password,
                created_at=time.time(),
            ))
        logger.info(f"Generated {count} email account(s) (@{self.domain})")
        return accounts

    def generate_bulk(self, count: int, prefix: str = "tix") -> list:
        """Generate many accounts at once."""
        return self.generate(prefix=prefix, count=count)
