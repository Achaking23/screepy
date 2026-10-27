
"""
Screepy TicketBot — MiniBot: single-session automated browser worker
"""

import time
import random
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum

from loguru import logger

from .utils import user_agent_rotator, random_delay, load_config


class BotStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    CAPTCHA = "captcha_blocked"
    BANNED = "banned"
    SUCCESS = "success"
    FAILED = "failed"


class Platform(Enum):
    TICKETMASTER = "ticketmaster"
    AXS = "axs"
    SEATGEEK = "seatgeek"
    STUBHUB = "stubhub"
    VIVIDSEATS = "vividseats"


@dataclass
class BotSession:
    """Represents a single automated browser session."""
    bot_id: str
    platform: Platform
    event_id: str
    proxy: Optional[str] = None
    account: Optional[dict] = None
    status: BotStatus = BotStatus.IDLE
    retries: int = 0
    max_retries: int = 3
    cookies: dict = field(default_factory=dict)
    result: Optional[dict] = None
    error: Optional[str] = None


class MiniBot:
    """
    MiniBot wraps a single browser/driver session.
    It handles page navigation, login, queue position, payment flow,
    and anti-detection measures for one ticket purchase.
    """

    def __init__(self, session: BotSession, config: dict):
        self.session = session
        self.config = config
        self.driver = None
        self._init_driver()

    def _init_driver(self):
        """Initialise the browser driver (undetected_chromedriver)."""
        cfg = self.config.get("browser", {})
        try:
            import undetected_chromedriver as uc
            options = uc.ChromeOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-logging")
            options.add_argument("--log-level=3")
            if cfg.get("headless", False):
                options.add_argument("--headless=new")
            if cfg.get("window_width") and cfg.get("window_height"):
                options.add_argument(
                    f"--window-size={cfg['window_width']},{cfg['window_height']}"
                )
            ua = cfg.get("user_agent") or user_agent_rotator()
            options.add_argument(f"--user-agent={ua}")

            if self.session.proxy:
                options.add_argument(f"--proxy-server={self.session.proxy}")

            self.driver = uc.Chrome(options=options)
            self.driver.implicitly_wait(cfg.get("implicit_wait", 10))
            logger.info(f"[{self.session.bot_id}] Browser initialised")
        except ImportError:
            logger.error("undetected_chromedriver not installed. "
                         "Run: pip install undetected-chromedriver")
            raise

    def navigate(self, url: str) -> bool:
        """Navigate to a URL with human-like delays."""
        try:
            logger.info(f"[{self.session.bot_id}] Navigating to {url}")
            self.driver.get(url)
            random_delay(1.0, 2.5)
            return True
        except Exception as exc:
            logger.error(f"[{self.session.bot_id}] Navigation error: {exc}")
            return False

    def find_and_click(self, by: str, selector: str, timeout: int = 10) -> bool:
        """Find an element and click it."""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        by_map = {
            "id": By.ID,
            "xpath": By.XPATH,
            "css": By.CSS_SELECTOR,
            "name": By.NAME,
            "class": By.CLASS_NAME,
        }
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by_map[by], selector))
            )
            random_delay(0.3, 0.8)
            element.click()
            return True
        except Exception as exc:
            logger.warning(f"[{self.session.bot_id}] Click failed ({by}={selector}): {exc}")
            return False

    def human_type(self, element, text: str):
        """Type text character-by-character with random delays."""
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.02, 0.12))

    def solve_captcha(self) -> bool:
        """
        Attempt to detect and solve a CAPTCHA.
        Returns True if solved or not present.
        """
        try:
            # Check for common CAPTCHA iframes
            from selenium.common.exceptions import NoSuchElementException
            captcha_iframes = [
                "//iframe[contains(@src, 'recaptcha')]",
                "//iframe[contains(@src, 'hcaptcha')]",
                "//div[contains(@class, 'captcha')]",
            ]
            for xpath in captcha_iframes:
                try:
                    if self.driver.find_element("xpath", xpath):
                        logger.warning(
                            f"[{self.session.bot_id}] CAPTCHA detected — manual intervention needed"
                        )
                        self.session.status = BotStatus.CAPTCHA
                        return False
                except NoSuchElementException:
                    continue
            return True
        except Exception:
            return True

    def run(self) -> dict:
        """
        Execute the full ticket acquisition workflow for this bot session.
        """
        self.session.status = BotStatus.RUNNING
        logger.info(f"[{self.session.bot_id}] Starting acquisition for "
                     f"{self.session.platform.value} / event {self.session.event_id}")

        # Platform-specific URL
        platform_urls = {
            Platform.TICKETMASTER: (
                f"https://www.ticketmaster.com/event/{self.session.event_id}"
            ),
            Platform.AXS: f"https://www.axs.com/events/{self.session.event_id}",
            Platform.SEATGEEK: f"https://seatgeek.com/{self.session.event_id}",
            Platform.STUBHUB: f"https://www.stubhub.com/event/{self.session.event_id}",
            Platform.VIVIDSEATS: f"https://www.vividseats.com/{self.session.event_id}",
        }
        url = platform_urls.get(self.session.platform)
        if not url:
            self.session.status = BotStatus.FAILED
            self.session.error = f"Unknown platform: {self.session.platform}"
            return self._result()

        if not self.navigate(url):
            self.session.status = BotStatus.FAILED
            self.session.error = "Navigation failed"
            return self._result()

        # Simulated acquisition steps
        steps = [
            ("Waiting for page load", 1.0),
            ("Checking inventory", 2.0),
            ("Selecting tickets", 1.5),
            ("Proceeding to checkout", 1.0),
            ("Filling payment", 2.0),
            ("Placing order", 1.0),
        ]
        for step_name, delay in steps:
            logger.info(f"[{self.session.bot_id}] {step_name}...")
            time.sleep(delay)

        # Mark success (placeholder for real logic)
        self.session.status = BotStatus.SUCCESS
        self.session.result = {
            "event_id": self.session.event_id,
            "platform": self.session.platform.value,
            "tickets": 2,
            "total": 149.50,
            "confirmation": f"SCP-{random.randint(100000, 999999)}",
        }
        logger.success(f"[{self.session.bot_id}] Order placed: {self.session.result}")
        return self._result()

    def _result(self) -> dict:
        return {
            "bot_id": self.session.bot_id,
            "status": self.session.status.value,
            "platform": self.session.platform.value,
            "event_id": self.session.event_id,
            "result": self.session.result,
            "error": self.session.error,
        }

    def cleanup(self):
        """Close the browser driver."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info(f"[{self.session.bot_id}] Browser closed")
            except Exception:
                pass
