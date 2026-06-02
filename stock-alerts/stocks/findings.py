import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

FINDINGS_FILE = Path("bot_findings.jsonl")
REQUIRED_KEYS = {"ticker", "discovered", "why_buy", "status"}


def load_findings() -> list[dict]:
    """
    Read bot_findings.jsonl and return a list of valid finding dicts.
    Lines that are blank, start with '#', or fail validation are skipped
    with a warning — a single bad line never crashes the whole run.
    """
    if not FINDINGS_FILE.exists():
        logger.info("No bot_findings.jsonl found — skipping.")
        return []

    findings = []
    for i, raw in enumerate(FINDINGS_FILE.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            logger.warning("bot_findings line %d: invalid JSON (%s) — skipping", i, exc)
            continue

        missing = REQUIRED_KEYS - obj.keys()
        if missing:
            logger.warning("bot_findings line %d: missing keys %s — skipping", i, missing)
            continue

        if not isinstance(obj["ticker"], str) or not obj["ticker"].strip():
            logger.warning("bot_findings line %d: ticker must be a non-empty string — skipping", i)
            continue

        buy_target = obj.get("buy_target")
        if buy_target is not None:
            try:
                obj["buy_target"] = float(buy_target)
            except (TypeError, ValueError):
                logger.warning("bot_findings line %d: buy_target must be a number or null — skipping", i)
                continue

        findings.append(obj)

    logger.info("Loaded %d finding(s) from bot_findings.jsonl", len(findings))
    return findings
