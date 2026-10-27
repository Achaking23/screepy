# 🕷️ Screepy TicketBot

**Automated ticket acquisition for major ticketing platforms.**

Screepy is a modular Python framework that monitors, analyses, and acquires
tickets from platforms like **Ticketmaster**, **AXS**, **SeatGeek**,
**StubHub**, and **VividSeats** using concurrent browser automation.

---

## ⚠️ Legal & Ethical Disclaimer

> **This project is for educational and research purposes only.**
>
> Using automated tools to purchase tickets may violate the Terms of Service
> of ticketing platforms. Many sites employ anti-bot measures and may
> permanently ban accounts or IP addresses detected automating purchases.
>
> **The authors assume no liability for misuse.** Use responsibly and only
> on platforms that permit automated access.

---

## ✨ Features

| Feature | Description |
|---|---|
| **Multi-platform** | Ticketmaster, AXS, SeatGeek, StubHub, VividSeats |
| **Concurrent bots** | Launch multiple browser instances in parallel |
| **Anti-detection** | Undetected ChromeDriver, human typing, random delays, UA rotation |
| **Account management** | Generate disposable emails, track bans & cooldowns |
| **Proxy rotation** | HTTP/SOCKS proxies with health checks & ban tracking |
| **Inventory monitoring** | Watch events for availability / price drops |
| **Payment handling** | Multi-card profiles with retry logic |
| **Notifications** | Desktop toasts, Telegram, Discord, Email |
| **Excel export** | Export inventory, results, and accounts to `.xlsx` |
| **CLI + Shell** | Full command-line interface + interactive shell |

---

## 📦 Installation

```bash
# 1. Clone the repository
git clone https://github.com/Achaking23/screepy.git
cd screepy

# 2. (Recommended) Create a virtual environment
python -m venv venv
source venv/bin/activate    # Linux/macOS
venv\Scripts\activate       # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) Install Playwright browsers
playwright install
```

---

## 🚀 Quick Start

### Acquire tickets for an event

```bash
python manage.py acquire \
    --platform ticketmaster \
    --event 123ABC \
    --quantity 2 \
    --bots 5
```

### Monitor an event for price changes

```bash
python manage.py monitor \
    --platform seatgeek \
    --event 456DEF \
    --interval 30
```

### Generate disposable accounts

```bash
python manage.py accounts create \
    --platform ticketmaster \
    --count 20
```

### Export results to Excel

```bash
python manage.py export results
```

### Run health checks

```bash
python manage.py health
```

### Interactive shell

```bash
python manage.py shell
```

---

## 📁 Project Structure

```
screepy/
├── manage.py                  # CLI entry point
├── bots/
│   ├── __init__.py
│   ├── bot_manager.py         # Orchestrates multiple MiniBot sessions
│   ├── mini_bot.py            # Single browser automation worker
│   └── utils.py               # Shared utilities (config, UA, delays)
├── accounts/
│   ├── __init__.py
│   ├── account_manager.py     # Account pool lifecycle & persistence
│   └── email_generator.py     # Disposable email / password generation
├── tickets/
│   ├── __init__.py
│   ├── ticket_monitor.py      # Event availability / price monitoring
│   ├── ticket_acquirer.py     # End-to-end acquisition orchestrator
│   └── inventory_manager.py   # Inventory storage & price-trend analysis
├── payments/
│   ├── __init__.py
│   └── payment_manager.py     # Card management & payment processing
├── proxies/
│   ├── __init__.py
│   ├── proxy_manager.py       # Proxy pool with health checks & rotation
│   └── list.txt               # Proxy list (one per line)
├── excel_export/
│   ├── __init__.py
│   └── exporter.py            # Excel (.xlsx) export with formatting
├── notifications/
│   ├── __init__.py
│   └── notifier.py            # Desktop, Telegram, Discord, Email alerts
├── config/
│   └── settings.yaml          # Global configuration
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

---

## ⚙️ Configuration

Edit `config/settings.yaml` to set:

- **Platform API keys** – optional (some platforms have public endpoints)
- **Browser settings** – headless mode, window size, timeouts
- **Proxy settings** – enable/disable, provider, source file
- **Notification channels** – Telegram bot token, Discord webhook, SMTP
- **Anti-detection** – delay ranges, human typing, user-agent rotation

---

## 🧪 Dependencies

- `undetected-chromedriver` / `selenium` / `playwright` – browser automation
- `requests` / `httpx` – HTTP clients
- `beautifulsoup4` / `lxml` – HTML parsing
- `openpyxl` – Excel export
- `plyer` – desktop notifications
- `python-telegram-bot` / `discord-webhook` – messaging
- `loguru` – logging

Full list in [`requirements.txt`](requirements.txt).

---

## 🤝 Contributing

Pull requests are welcome. Please:

1. Fork the repo
2. Create a feature branch
3. Write tests for new functionality
4. Submit a PR with a clear description

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

*Built with ❤️ by [Achaking23](https://github.com/Achaking23)*


## 📦 Vendored Dependencies

`undetected_chromedriver` is vendored under `vendored/` because its
pip wheel build has a known issue on Windows. It's loaded automatically
by `manage.py` — no extra install step needed.
