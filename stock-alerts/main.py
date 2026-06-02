import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from config import load_config
from stocks.portfolio import OWNED, WATCHLIST, ALERT_RULES
from stocks.watcher import fetch_quotes
from alerts.rules import evaluate
from alerts.sms import send_alerts

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

COOLDOWN_FILE = Path(".cooldowns.json")
ET = ZoneInfo("America/New_York")


def is_market_open() -> bool:
    now = datetime.now(ET)
    if now.weekday() >= 5:  # Sat=5, Sun=6
        return False
    open_dt = now.replace(hour=9, minute=30, second=0, microsecond=0)
    close_dt = now.replace(hour=16, minute=0, second=0, microsecond=0)
    return open_dt <= now < close_dt


def load_cooldowns() -> dict:
    if COOLDOWN_FILE.exists():
        try:
            return json.loads(COOLDOWN_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_cooldowns(cooldowns: dict) -> None:
    COOLDOWN_FILE.write_text(json.dumps(cooldowns, indent=2))


def apply_cooldowns(alerts: list[dict], cooldowns: dict, cooldown_minutes: int) -> list[dict]:
    now = datetime.now(timezone.utc).timestamp()
    surviving = []
    for alert in alerts:
        key = f"{alert['ticker']}:{alert['type']}"
        last_sent = cooldowns.get(key, 0)
        elapsed = now - last_sent
        if elapsed >= cooldown_minutes * 60:
            surviving.append(alert)
        else:
            remaining = int((cooldown_minutes * 60 - elapsed) / 60)
            logger.info("Cooldown: skipping %s (%d min remaining)", key, remaining)
    return surviving


def record_sent(alerts: list[dict], cooldowns: dict) -> dict:
    now = datetime.now(timezone.utc).timestamp()
    for alert in alerts:
        key = f"{alert['ticker']}:{alert['type']}"
        cooldowns[key] = now
    return cooldowns


def main() -> None:
    logger.info("=== Stock Alert Run ===")

    if not is_market_open():
        logger.info("Market is closed — exiting.")
        sys.exit(0)
    logger.info("Market is open.")

    config = load_config()

    owned_tickers = [s["ticker"] for s in OWNED]
    watch_tickers = [s["ticker"] for s in WATCHLIST]
    all_tickers = list(dict.fromkeys(owned_tickers + watch_tickers))

    logger.info("Fetching quotes for: %s", ", ".join(all_tickers))
    quotes = fetch_quotes(all_tickers)
    if not quotes:
        logger.warning("No quotes returned — exiting.")
        sys.exit(0)

    alerts = evaluate(quotes)
    logger.info("%d alert(s) before cooldown.", len(alerts))

    cooldowns = load_cooldowns()
    cooldown_minutes = ALERT_RULES.get("cooldown_minutes", 60)
    alerts = apply_cooldowns(alerts, cooldowns, cooldown_minutes)
    logger.info("%d alert(s) after cooldown.", len(alerts))

    if not alerts:
        logger.info("Nothing to send.")
        sys.exit(0)

    send_alerts(config, alerts)

    cooldowns = record_sent(alerts, cooldowns)
    save_cooldowns(cooldowns)
    logger.info("Done. Cooldowns saved.")


if __name__ == "__main__":
    main()
