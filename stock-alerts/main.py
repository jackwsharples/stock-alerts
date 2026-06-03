import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from config import load_config
from stocks.portfolio import OWNED, WATCHLIST, ALERT_RULES, MUTED_FINDINGS
from stocks.findings import load_findings
from stocks.watcher import fetch_quotes
from stocks.tracker import (update_tracking, write_scorecard, save_tracking,
                             weekly_summary_message, should_send_weekly_summary,
                             mark_weekly_summary_sent)
from alerts.rules import evaluate
from alerts.sms import send_alerts, send_notification

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

COOLDOWN_FILE = Path(".cooldowns.json")
SEEN_FINDINGS_FILE = Path(".seen_findings.json")
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


def load_seen_findings() -> dict:
    if SEEN_FINDINGS_FILE.exists():
        try:
            return json.loads(SEEN_FINDINGS_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_seen_findings(seen: dict) -> None:
    SEEN_FINDINGS_FILE.write_text(json.dumps(seen, indent=2))


def announce_new_findings(config: dict, findings: list[dict], seen: dict) -> dict:
    """Send a 'new pick' notification for any finding not yet announced."""
    now = datetime.now(timezone.utc).timestamp()
    for finding in findings:
        if finding.get("status") != "new":
            continue
        key = f"{finding['ticker']}:{finding['discovered']}"
        if key in seen:
            continue

        ticker = finding["ticker"]
        buy_target = finding.get("buy_target")
        lines = [
            f"Thesis: {finding['why_buy']}",
            f"Source: {finding.get('source', 'unknown')}",
        ]
        if buy_target is not None:
            lines.append(f"Suggested entry: ${buy_target:.2f}")

        send_notification(
            config,
            "\n".join(lines),
            title=f"New Research Pick: {ticker}",
            priority="default",
            tag="mag",
        )
        seen[key] = now
        logger.info("Announced new finding: %s", ticker)

    return seen


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

    findings = load_findings()
    seen_findings = load_seen_findings()
    seen_findings = announce_new_findings(config, findings, seen_findings)
    save_seen_findings(seen_findings)

    # Build a watchlist from bot findings, skipping tickers already in OWNED/WATCHLIST
    existing_tickers = {s["ticker"] for s in OWNED} | {s["ticker"] for s in WATCHLIST}
    findings_watchlist = [
        {"ticker": f["ticker"], "buy_target": f.get("buy_target")}
        for f in findings
        if f["ticker"] not in existing_tickers and f["ticker"] not in MUTED_FINDINGS
    ]
    if findings_watchlist:
        logger.info("Watching %d bot finding(s): %s",
                    len(findings_watchlist),
                    ", ".join(f["ticker"] for f in findings_watchlist))

    owned_tickers = [s["ticker"] for s in OWNED]
    watch_tickers = [s["ticker"] for s in WATCHLIST]
    finding_tickers = [f["ticker"] for f in findings_watchlist]
    all_tickers = list(dict.fromkeys(owned_tickers + watch_tickers + finding_tickers))

    logger.info("Fetching quotes for: %s", ", ".join(all_tickers))
    quotes = fetch_quotes(all_tickers)
    if not quotes:
        logger.warning("No quotes returned — exiting.")
        sys.exit(0)

    # Performance tracking — snapshot entry prices and update metrics
    tracking = update_tracking(findings, quotes)
    write_scorecard(tracking)
    if should_send_weekly_summary(tracking):
        send_notification(
            config,
            weekly_summary_message(tracking),
            title="Bot Picks Weekly Recap",
            priority="default",
            tag="bar_chart",
        )
        tracking = mark_weekly_summary_sent(tracking)
        logger.info("Weekly summary sent.")
    save_tracking(tracking)

    alerts = evaluate(quotes, extra_watchlist=findings_watchlist)
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
