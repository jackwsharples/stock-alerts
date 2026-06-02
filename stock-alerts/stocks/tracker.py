import json
import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

TRACKING_FILE = Path(".findings_tracking.json")
SCORECARD_FILE = Path("bot_performance.md")
ET = ZoneInfo("America/New_York")


def _pct(current: float, reference: float) -> float:
    if reference == 0:
        return 0.0
    return (current - reference) / reference * 100


def _days_held(entry_date: str) -> int:
    try:
        entry = datetime.strptime(entry_date, "%Y-%m-%d").date()
        return (datetime.now(ET).date() - entry).days
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def load_tracking() -> dict:
    if TRACKING_FILE.exists():
        try:
            return json.loads(TRACKING_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_tracking(tracking: dict) -> None:
    TRACKING_FILE.write_text(json.dumps(tracking, indent=2))


# ---------------------------------------------------------------------------
# Core update logic
# ---------------------------------------------------------------------------

def update_tracking(findings: list[dict], quotes: dict[str, dict]) -> dict:
    """
    For each finding that has a live quote:
      - First run: snapshot entry_price (never overwritten again).
      - Every run: update current_price, pct_return, max/min prices,
        max_gain_pct, max_drawdown_pct, target_hit.

    Returns the full tracking dict (including _meta).
    Caller is responsible for calling save_tracking().
    """
    tracking = load_tracking()
    today = datetime.now(ET).strftime("%Y-%m-%d")

    for finding in findings:
        ticker = finding["ticker"]
        if ticker not in quotes:
            continue

        key = f"{ticker}:{finding['discovered']}"
        price = quotes[ticker]["price"]
        buy_target = finding.get("buy_target")

        if key not in tracking:
            tracking[key] = {
                "ticker": ticker,
                "discovered": finding["discovered"],
                "why_buy": finding["why_buy"],
                "source": finding.get("source", ""),
                "buy_target": buy_target,
                "entry_price": price,       # snapshotted once, never overwritten
                "entry_date": today,
                "current_price": price,
                "last_updated": today,
                "pct_return": 0.0,
                "max_price": price,
                "min_price": price,
                "max_gain_pct": 0.0,
                "max_drawdown_pct": 0.0,
                "target_hit": False,
            }
            logger.info("Tracker: snapshotted entry for %s @ $%.2f", ticker, price)
        else:
            rec = tracking[key]
            entry = rec["entry_price"]      # never touch this

            rec["current_price"] = price
            rec["last_updated"] = today
            rec["pct_return"] = _pct(price, entry)

            if price > rec["max_price"]:
                rec["max_price"] = price
            if price < rec["min_price"]:
                rec["min_price"] = price

            rec["max_gain_pct"] = _pct(rec["max_price"], entry)
            rec["max_drawdown_pct"] = _pct(rec["min_price"], entry)

            if buy_target is not None and not rec["target_hit"] and price <= buy_target:
                rec["target_hit"] = True
                logger.info("Tracker: %s hit buy target $%.2f", ticker, buy_target)

            logger.info("Tracker: updated %s  return=%+.1f%%", ticker, rec["pct_return"])

    return tracking


# ---------------------------------------------------------------------------
# Scorecard
# ---------------------------------------------------------------------------

def write_scorecard(tracking: dict) -> None:
    """Write bot_performance.md from current tracking state."""
    picks = [v for v in tracking.values() if isinstance(v, dict) and "entry_price" in v]
    today = datetime.now(ET).strftime("%Y-%m-%d")

    lines = [
        "# Bot Research Pick Scorecard",
        "",
        f"_Last updated: {today}_",
        "",
        "Entry prices are live market prices captured by the tracker on first discovery.",
        "All data sourced from yfinance — agent self-reporting is not used.",
        "",
    ]

    if not picks:
        lines.append("_No picks tracked yet._")
        SCORECARD_FILE.write_text("\n".join(lines))
        logger.info("Scorecard written (no picks yet).")
        return

    lines += [
        "## Picks",
        "",
        "| Ticker | Discovered | Entry $ | Current $ | Return | Max Gain | Max DD | Days | Buy Target | Target Hit |",
        "|--------|------------|---------|-----------|--------|----------|--------|------|------------|------------|",
    ]

    for rec in sorted(picks, key=lambda r: r["discovered"]):
        days = _days_held(rec["entry_date"])
        bt = rec["buy_target"]
        bt_str = f"${bt:.2f}" if bt is not None else "—"
        hit_str = ("Yes ✓" if rec["target_hit"] else "No") if bt is not None else "—"
        lines.append(
            f"| {rec['ticker']} | {rec['discovered']} "
            f"| ${rec['entry_price']:.2f} | ${rec['current_price']:.2f} "
            f"| {rec['pct_return']:+.1f}% | {rec['max_gain_pct']:+.1f}% "
            f"| {rec['max_drawdown_pct']:+.1f}% | {days} "
            f"| {bt_str} | {hit_str} |"
        )

    returns = [r["pct_return"] for r in picks]
    avg = sum(returns) / len(returns)
    best = max(picks, key=lambda r: r["pct_return"])
    worst = min(picks, key=lambda r: r["pct_return"])
    with_targets = [r for r in picks if r["buy_target"] is not None]
    targets_hit = sum(1 for r in with_targets if r["target_hit"])

    lines += [
        "",
        "## Summary",
        "",
        f"- **Picks tracked:** {len(picks)}",
        f"- **Average return:** {avg:+.1f}%",
        f"- **Best pick:** {best['ticker']} ({best['pct_return']:+.1f}%)",
        f"- **Worst pick:** {worst['ticker']} ({worst['pct_return']:+.1f}%)",
    ]
    if with_targets:
        lines.append(f"- **Buy targets hit:** {targets_hit} / {len(with_targets)}")

    SCORECARD_FILE.write_text("\n".join(lines) + "\n")
    logger.info("Scorecard written to %s", SCORECARD_FILE)


# ---------------------------------------------------------------------------
# Weekly summary (ntfy)
# ---------------------------------------------------------------------------

def weekly_summary_message(tracking: dict) -> str:
    """Compact multi-line message for the weekly ntfy recap."""
    picks = [v for v in tracking.values() if isinstance(v, dict) and "entry_price" in v]
    if not picks:
        return "Bot picks weekly recap: no picks tracked yet."

    sorted_picks = sorted(picks, key=lambda r: r["pct_return"], reverse=True)
    lines = [f"Weekly recap — {len(picks)} bot pick(s):"]
    for rec in sorted_picks:
        days = _days_held(rec["entry_date"])
        hit = " ✓" if rec.get("target_hit") else ""
        lines.append(f"  {rec['ticker']}: {rec['pct_return']:+.1f}% ({days}d){hit}")

    returns = [r["pct_return"] for r in picks]
    avg = sum(returns) / len(returns)
    best = max(picks, key=lambda r: r["pct_return"])
    worst = min(picks, key=lambda r: r["pct_return"])
    lines.append(
        f"Avg {avg:+.1f}% | Best {best['ticker']} {best['pct_return']:+.1f}%"
        f" | Worst {worst['ticker']} {worst['pct_return']:+.1f}%"
    )
    return "\n".join(lines)


def should_send_weekly_summary(tracking: dict) -> bool:
    """True on Monday if we haven't sent a summary this ISO week yet."""
    today = datetime.now(ET).date()
    if today.weekday() != 0:  # Monday = 0
        return False
    meta = tracking.get("_meta", {})
    last_str = meta.get("last_weekly_summary", "")
    if not last_str:
        return True
    try:
        last_date = datetime.strptime(last_str, "%Y-%m-%d").date()
        return last_date.isocalendar()[:2] != today.isocalendar()[:2]
    except Exception:
        return True


def mark_weekly_summary_sent(tracking: dict) -> dict:
    today = datetime.now(ET).strftime("%Y-%m-%d")
    tracking.setdefault("_meta", {})["last_weekly_summary"] = today
    return tracking
