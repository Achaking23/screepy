#!/usr/bin/env python3
"""
Screepy TicketBot — CLI Entry Point
=====================================
Usage:
    python manage.py acquire --platform ticketmaster --event "123abc" --qty 2 --bots 3
    python manage.py monitor --platform ticketmaster --event "123abc"
    python manage.py accounts create --platform ticketmaster --count 10
    python manage.py export results
    python manage.py health
    python manage.py shell
"""

import sys
import argparse
import time
from pathlib import Path

# Ensure project root is on sys.path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))
vendored = project_root / "vendored"
if vendored.exists():
    sys.path.insert(0, str(vendored))

from loguru import logger


def main():
    parser = argparse.ArgumentParser(
        prog="screepy",
        description="Screepy TicketBot — automated ticket acquisition",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python manage.py acquire -p ticketmaster -e 123ABC -q 2 -b 5
  python manage.py monitor -p ticketmaster -e 123ABC
  python manage.py accounts create -p ticketmaster -c 20
  python manage.py export results
  python manage.py health
        """,
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug-level logging",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── acquire ──────────────────────────────────────────────
    acq = subparsers.add_parser("acquire", help="Acquire tickets for an event")
    acq.add_argument("-p", "--platform", required=True,
                     choices=["ticketmaster", "axs", "seatgeek", "stubhub", "vividseats"])
    acq.add_argument("-e", "--event", required=True, help="Event ID")
    acq.add_argument("-q", "--quantity", type=int, default=2, help="Number of tickets")
    acq.add_argument("-b", "--bots", type=int, default=3, help="Number of concurrent bots")
    acq.add_argument("--max-price", type=float, default=0, help="Max price per ticket")
    acq.add_argument("--presale", action="store_true", help="Presale event")
    acq.add_argument("--email", help="Account email (optional)")
    acq.add_argument("--password", help="Account password (optional)")

    # ── monitor ──────────────────────────────────────────────
    mon = subparsers.add_parser("monitor", help="Monitor an event for availability/price changes")
    mon.add_argument("-p", "--platform", required=True,
                     choices=["ticketmaster", "axs", "seatgeek", "stubhub", "vividseats"])
    mon.add_argument("-e", "--event", required=True, help="Event ID")
    mon.add_argument("-i", "--interval", type=int, default=60, help="Check interval (seconds)")

    # ── accounts ──────────────────────────────────────────────
    acc = subparsers.add_parser("accounts", help="Manage platform accounts")
    acc_sub = acc.add_subparsers(dest="action", help="Account action")

    acc_create = acc_sub.add_parser("create", help="Create new accounts")
    acc_create.add_argument("-p", "--platform", required=True,
                            choices=["ticketmaster", "axs", "seatgeek", "stubhub", "vividseats"])
    acc_create.add_argument("-c", "--count", type=int, default=5, help="Number of accounts")
    acc_create.add_argument("--domain", help="Email domain (default: random disposable)")

    acc_stats = acc_sub.add_parser("stats", help="Show account pool statistics")

    # ── export ──────────────────────────────────────────────
    exp = subparsers.add_parser("export", help="Export data to Excel")
    exp.add_argument("type", choices=["results", "accounts", "inventory"],
                     help="Data type to export")
    exp.add_argument("-o", "--output", help="Output filename (optional)")

    # ── health ──────────────────────────────────────────────
    subparsers.add_parser("health", help="Run health checks on proxies & accounts")

    # ── shell ──────────────────────────────────────────────
    subparsers.add_parser("shell", help="Open an interactive Python shell with modules loaded")

    # ── Parse ──────────────────────────────────────────────
    args = parser.parse_args()

    if args.verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    else:
        logger.add(sys.stderr, level="INFO")

    if not args.command:
        parser.print_help()
        return

    # Route to command handlers
    command_map = {
        "acquire": cmd_acquire,
        "monitor": cmd_monitor,
        "accounts": cmd_accounts,
        "export": cmd_export,
        "health": cmd_health,
        "shell": cmd_shell,
    }

    handler = command_map.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()


# ── Command implementations ──────────────────────────────────


def cmd_acquire(args):
    """Acquire tickets for an event."""
    from tickets.ticket_acquirer import TicketAcquirer, AcquisitionPlan
    from bots.mini_bot import Platform

    plat_map = {
        "ticketmaster": Platform.TICKETMASTER,
        "axs": Platform.AXS,
        "seatgeek": Platform.SEATGEEK,
        "stubhub": Platform.STUBHUB,
        "vividseats": Platform.VIVIDSEATS,
    }

    plan = AcquisitionPlan(
        platform=plat_map[args.platform],
        event_id=args.event,
        quantity=args.quantity,
        bots_count=args.bots,
        max_price=args.max_price,
        presale=args.presale,
        account_email=args.email,
        account_password=args.password,
    )

    acquirer = TicketAcquirer()
    result = acquirer.acquire(plan)

    if result.success:
        print(f"\n✅ SUCCESS — {result.tickets_acquired} ticket(s) acquired!")
        print(f"   Confirmation: {result.confirmation_code}")
        print(f"   Total paid:   ${result.total_paid:.2f}")
    else:
        print(f"\n❌ FAILED — {result.error}")


def cmd_monitor(args):
    """Monitor an event for availability/price changes."""
    from tickets.ticket_monitor import TicketMonitor

    monitor = TicketMonitor(check_interval=args.interval)
    monitor.add_event(platform=args.platform, event_id=args.event)

    def on_change(event):
        print(
            f"[{event.last_checked.strftime('%H:%M:%S')}] "
            f"{event.event_id} → {event.status.value} "
            f"(${event.min_price:.2f} – ${event.max_price:.2f})"
        )

    monitor.on_change(on_change)
    print(f"Monitoring {args.platform}/{args.event} every {args.interval}s...")
    print("Press Ctrl+C to stop.\n")

    try:
        monitor.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        monitor.stop()
        print("\nMonitoring stopped.")


def cmd_accounts(args):
    """Manage platform accounts."""
    from accounts.account_manager import AccountManager

    mgr = AccountManager()

    if args.action == "create":
        accounts = mgr.create_accounts(
            platform=args.platform,
            count=args.count,
            domain=args.domain,
        )
        print(f"\nCreated {len(accounts)} account(s) for {args.platform}:")
        for acc in accounts:
            print(f"  {acc.email} | {acc.password}")

    elif args.action == "stats" or not args.action:
        stats = mgr.get_stats()
        print("\n📊 Account Pool Statistics:")
        print(f"  Total:     {stats['total']}")
        print(f"  Verified:  {stats['verified']}")
        print(f"  Banned:    {stats['banned']}")
        print(f"  Platforms: {', '.join(stats['platforms']) or 'none'}")


def cmd_export(args):
    """Export data to Excel."""
    from excel_export.exporter import Exporter
    exporter = Exporter()

    if args.type == "results":
        path = exporter.export_results([])
        print(f"Results exported to: {path}")
    elif args.type == "accounts":
        path = exporter.export_accounts([])
        print(f"Accounts exported to: {path}")
    elif args.type == "inventory":
        path = exporter.export_inventory([])
        print(f"Inventory exported to: {path}")


def cmd_health(args):
    """Run health checks."""
    from proxies.proxy_manager import ProxyManager
    from accounts.account_manager import AccountManager

    print("\n🔍 Running health checks...\n")

    # Proxies
    pm = ProxyManager()
    pm.health_check_all()
    proxy_stats = pm.get_stats()
    print(f"Proxies: {proxy_stats['alive']}/{proxy_stats['total']} alive")

    # Accounts
    am = AccountManager()
    acc_stats = am.get_stats()
    print(f"Accounts: {acc_stats['total']} total, {acc_stats['banned']} banned")

    print("\n✅ Health check complete.")


def cmd_shell(args):
    """Open an interactive Python shell with modules preloaded."""
    import code
    import readline
    import rlcompleter

    # Pre-load commonly used modules
    namespace = {
        "BotManager": __import__("bots.bot_manager", fromlist=["BotManager"]).BotManager,
        "MiniBot": __import__("bots.mini_bot", fromlist=["MiniBot"]).MiniBot,
        "Platform": __import__("bots.mini_bot", fromlist=["Platform"]).Platform,
        "AccountManager": __import__("accounts.account_manager", fromlist=["AccountManager"]).AccountManager,
        "TicketAcquirer": __import__("tickets.ticket_acquirer", fromlist=["TicketAcquirer"]).TicketAcquirer,
        "TicketMonitor": __import__("tickets.ticket_monitor", fromlist=["TicketMonitor"]).TicketMonitor,
        "InventoryManager": __import__("tickets.inventory_manager", fromlist=["InventoryManager"]).InventoryManager,
        "PaymentManager": __import__("payments.payment_manager", fromlist=["PaymentManager"]).PaymentManager,
        "ProxyManager": __import__("proxies.proxy_manager", fromlist=["ProxyManager"]).ProxyManager,
        "Exporter": __import__("excel_export.exporter", fromlist=["Exporter"]).Exporter,
        "Notifier": __import__("notifications.notifier", fromlist=["Notifier"]).Notifier,
        "EmailGenerator": __import__("accounts.email_generator", fromlist=["EmailGenerator"]).EmailGenerator,
        "load_config": __import__("bots.utils", fromlist=["load_config"]).load_config,
    "uc": __import__("undetected_chromedriver"),
    }

    banner = """
╔════════════════════════════════════════════╗
║        Screepy TicketBot — Shell           ║
╠════════════════════════════════════════════╣
║  Available: BotManager, MiniBot, Platform, ║
║  AccountManager, TicketAcquirer,           ║
║  TicketMonitor, InventoryManager,          ║
║  PaymentManager, ProxyManager, Exporter,   ║
║  Notifier, EmailGenerator, load_config     ║
╚════════════════════════════════════════════╝
"""
    code.interact(banner=banner, local=namespace)


if __name__ == "__main__":
    main()
