import logging
import requests

logger = logging.getLogger(__name__)

NTFY_BASE = "https://ntfy.sh"

# Maps alert type → (ntfy priority, emoji tag)
_ALERT_STYLE: dict[str, tuple[str, str]] = {
    "sell_target":    ("high",   "white_check_mark"),
    "stop_loss":      ("urgent", "warning"),
    "intraday_up":    ("default","chart_increasing"),
    "intraday_down":  ("high",   "chart_decreasing"),
    "buy_target":     ("high",   "bell"),
    "watchlist_dip":  ("default","eyes"),
}


def send_notification(config: dict, message: str, title: str = "Stock Alert",
                      priority: str = "default", tag: str = "chart_increasing") -> None:
    """Send a push notification via ntfy.sh."""
    resp = requests.post(
        f"{NTFY_BASE}/{config['NTFY_TOPIC']}",
        data=message.encode("utf-8"),
        headers={
            "Title": title,
            "Priority": priority,
            "Tags": tag,
        },
        timeout=10,
    )
    resp.raise_for_status()
    logger.info("Notification sent (status %d)", resp.status_code)


def send_alerts(config: dict, alerts: list[dict]) -> None:
    """Send each alert as a push notification."""
    for alert in alerts:
        logger.info("Sending: %s", alert["message"])
        priority, tag = _ALERT_STYLE.get(alert["type"], ("default", "bell"))
        send_notification(
            config,
            alert["message"],
            title=f"Stock Alert: {alert['ticker']}",
            priority=priority,
            tag=tag,
        )


if __name__ == "__main__":
    # Standalone test: python -m alerts.sms
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    try:
        from config import load_config
        cfg = load_config()
    except EnvironmentError as exc:
        print(f"Config error: {exc}")
        sys.exit(1)

    send_notification(cfg, "Stock-alerts test — ntfy.sh is wired up correctly!",
                      title="Test Alert", priority="default", tag="white_check_mark")
    print("Test notification sent. Check your phone.")
