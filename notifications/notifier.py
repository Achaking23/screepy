
"""
Screepy TicketBot — Notifier: sends alerts via desktop, Telegram, Discord, email
"""

from typing import Optional
from dataclasses import dataclass

from loguru import logger


@dataclass
class AlertMessage:
    """A notification message payload."""
    title: str
    body: str
    level: str = "info"  # info, success, warning, error
    event_id: str = ""
    platform: str = ""


class Notifier:
    """
    Sends notifications through multiple channels:
    - Desktop toast (plyer)
    - Telegram bot
    - Discord webhook
    - Email (SMTP)
    """

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}

    # ─── Desktop ───────────────────────────────────────────────

    def send_desktop(self, title: str, message: str) -> bool:
        """Send a desktop OS notification (toast)."""
        try:
            from plyer import notification
            notification.notify(
                title=title,
                message=message,
                app_name="Screepy TicketBot",
                timeout=5,
            )
            logger.debug(f"Desktop notification: {title}")
            return True
        except ImportError:
            logger.warning("plyer not installed; skipping desktop notification.")
            return False
        except Exception as exc:
            logger.error(f"Desktop notification failed: {exc}")
            return False

    # ─── Telegram ──────────────────────────────────────────────

    def send_telegram(self, message: str) -> bool:
        """Send a message via Telegram bot."""
        cfg = self.config.get("telegram", {})
        if not cfg.get("enabled"):
            return False

        bot_token = cfg.get("bot_token", "")
        chat_id = cfg.get("chat_id", "")
        if not bot_token or not chat_id:
            logger.warning("Telegram not configured (missing token/chat_id).")
            return False

        try:
            import requests
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            logger.debug(f"Telegram notification sent.")
            return True
        except Exception as exc:
            logger.error(f"Telegram send failed: {exc}")
            return False

    # ─── Discord ──────────────────────────────────────────────

    def send_discord(self, message: str) -> bool:
        """Send a message via Discord webhook."""
        cfg = self.config.get("discord", {})
        webhook_url = cfg.get("webhook_url", "")
        if not webhook_url:
            logger.warning("Discord webhook URL not configured.")
            return False

        try:
            from discord_webhook import DiscordWebhook
            webhook = DiscordWebhook(url=webhook_url, content=message)
            webhook.execute()
            logger.debug("Discord notification sent.")
            return True
        except ImportError:
            logger.warning("discord-webhook not installed.")
            return False
        except Exception as exc:
            logger.error(f"Discord send failed: {exc}")
            return False

    # ─── Email ────────────────────────────────────────────────

    def send_email(self, subject: str, body: str) -> bool:
        """Send an email notification via SMTP."""
        cfg = self.config.get("email", {})
        if not cfg.get("enabled"):
            return False

        smtp_server = cfg.get("smtp_server", "")
        smtp_port = cfg.get("smtp_port", 587)
        username = cfg.get("username", "")
        password = cfg.get("password", "")
        from_addr = cfg.get("from_addr", username)
        to_addr = cfg.get("to_addr", "")

        if not all([smtp_server, username, password, to_addr]):
            logger.warning("Email not fully configured.")
            return False

        try:
            import smtplib
            from email.mime.text import MIMEText

            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = from_addr
            msg["To"] = to_addr

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(username, password)
                server.send_message(msg)

            logger.debug(f"Email notification sent to {to_addr}")
            return True
        except Exception as exc:
            logger.error(f"Email send failed: {exc}")
            return False

    # ─── Unified ──────────────────────────────────────────────

    def alert(self, msg: AlertMessage):
        """
        Send an alert through all enabled channels.
        """
        formatted = f"[{msg.level.upper()}] {msg.title}\n{msg.body}"
        if msg.event_id:
            formatted += f"\nEvent: {msg.event_id}"
        if msg.platform:
            formatted += f" | Platform: {msg.platform}"

        # Desktop (always)
        self.send_desktop(msg.title, msg.body)

        # Telegram
        self.send_telegram(formatted)

        # Discord
        self.send_discord(formatted)

        # Email
        self.send_email(f"[Screepy] {msg.title}", formatted)

        logger.info(f"Alert sent: {msg.title}")

    def notify_success(self, platform: str, event_id: str, tickets: int, total: float):
        """Convenience: send a success notification."""
        msg = AlertMessage(
            title="✅ Tickets Acquired!",
            body=f"Successfully purchased {tickets} ticket(s) on {platform.upper()} "
                 f"for event {event_id}. Total: ${total:.2f}",
            level="success",
            event_id=event_id,
            platform=platform,
        )
        self.alert(msg)

    def notify_failure(self, platform: str, event_id: str, error: str):
        """Convenience: send a failure notification."""
        msg = AlertMessage(
            title="❌ Acquisition Failed",
            body=f"Failed to acquire tickets on {platform.upper()} "
                 f"for event {event_id}. Error: {error}",
            level="error",
            event_id=event_id,
            platform=platform,
        )
        self.alert(msg)

    def notify_price_drop(self, platform: str, event_id: str, old_price: float, new_price: float):
        """Convenience: send a price-drop alert."""
        msg = AlertMessage(
            title="💰 Price Drop!",
            body=f"Price dropped on {platform.upper()} for event {event_id}: "
                 f"${old_price:.2f} → ${new_price:.2f}",
            level="info",
            event_id=event_id,
            platform=platform,
        )
        self.alert(msg)
