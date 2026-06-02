# Stock Price Alerts

Monitors your portfolio every 5 minutes during US market hours and sends push
notifications to your phone via ntfy when prices hit your targets or move
sharply intraday. Also consumes research picks written by an AI agent and
notifies you of new finds, then tracks them like watchlist stocks.

## Notifications you'll receive

| Situation | Title |
|---|---|
| Owned stock reaches sell target | `Stock Alert: TICKER` |
| Owned stock hits stop-loss | `Stock Alert: TICKER` |
| Any owned stock moves ±5% from open | `Stock Alert: TICKER` |
| Watchlist stock drops to buy target | `Stock Alert: TICKER` |
| Watchlist stock drops ≥5% from open | `Stock Alert: TICKER` |
| Agent writes a new research pick | `New Research Pick: TICKER` 🔍 |

The ±5% intraday threshold and 60-minute repeat cooldown are both configurable
in `stocks/portfolio.py`.

---

## Local setup

### 1. Prerequisites

- Python 3.11+
- [ntfy](https://ntfy.sh) app installed on your phone (free, App Store / Google Play)

### 2. Install dependencies

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure your portfolio

Edit `stocks/portfolio.py` — this is the file you touch most often:

- `OWNED` — stocks you hold: ticker, cost basis, sell target, stop-loss
- `WATCHLIST` — stocks you want to buy on a dip: ticker, buy target, max buy
- `ALERT_RULES` — intraday threshold (default 5%) and cooldown (default 60 min)

### 4. Set up ntfy

1. Install the **ntfy** app on your phone.
2. Open the app → tap **+** → type your topic name → Subscribe.
   Your topic is in `.env` as `NTFY_TOPIC`. Keep it long and hard to guess —
   it's your only credential.
3. Copy `.env.example` to `.env` and fill in your topic:

```bash
cp .env.example .env
```

```
NTFY_TOPIC=stockalerts-yourname-randomsuffix
```

### 5. Test the notification pipeline

```bash
# Confirm price fetching works (run during market hours for live data)
python -m stocks.watcher

# Dry-run alert logic — prints what WOULD fire, no notification sent
python -m alerts.rules

# Send a test push notification to your phone
python -m alerts.sms

# Full run (market hours check, quotes, rules, cooldowns, notify)
python main.py
```

---

## Bot findings — research agent contract

An AI agent running separately can write stock picks to `bot_findings.jsonl`.
On every run, the app reads this file, notifies you of any new picks, and then
tracks those tickers with the same ongoing watchlist alert logic (intraday dips,
buy target hits).

### File: `bot_findings.jsonl`

One JSON object per line. The agent **appends only** — it never rewrites or
edits existing lines.

**Schema:**

```json
{
  "ticker":     "MSFT",
  "discovered": "2026-06-02",
  "why_buy":    "Agent's thesis — shown in the notification",
  "source":     "Where / how the agent flagged this",
  "buy_target": 380.00,
  "status":     "new"
}
```

| Field | Required | Notes |
|---|---|---|
| `ticker` | Yes | Yahoo Finance symbol (e.g. `BRK-B`, not `BRK.B`) |
| `discovered` | Yes | ISO date the agent found it (`YYYY-MM-DD`) |
| `why_buy` | Yes | Free-text thesis — shown verbatim in the notification |
| `source` | Yes | e.g. `"earnings_scan"`, `"reddit_monitor"` |
| `buy_target` | No | Suggested entry price, or `null` if none |
| `status` | Yes | Always write `"new"` — the app tracks what it has announced |

**Rules for the agent:**
- Append a line; never edit or delete existing lines.
- Always set `"status": "new"` — the app handles state in `.seen_findings.json`.
- After appending, `git push` to trigger a Railway redeploy. The app will pick
  up the new line on its next cron run.
- Never touch `stocks/portfolio.py` — that file belongs to the user.

### How findings flow into the app

```
bot_findings.jsonl
       │
       ▼
stocks/findings.py  →  load_findings()
       │
       ├─ New, unseen picks  →  send_notification() "New Research Pick: TICKER"
       │                         └─ announced ticker:date saved to .seen_findings.json
       │
       └─ All findings  →  added to watchlist fed into rules.evaluate()
                            └─ same intraday dip + buy_target alerts as WATCHLIST stocks
```

Malformed lines are logged and skipped — a single bad line never crashes a run.

---

## Deploying to Railway

### 1. Push to GitHub

```bash
git add .
git commit -m "your message"
git push
```

Pushing to `main` triggers an automatic Railway redeploy.

### 2. Create a Railway project (first time only)

1. Go to [railway.app](https://railway.app) and sign in with GitHub.
2. **New Project → Deploy from GitHub repo** → select `stock-alerts`.
3. Under **Variables**, add:
   ```
   NTFY_TOPIC = your-topic-name-here
   ```
4. Under **Settings → Start Command**, set:
   ```
   python main.py
   ```
5. Under **Settings → Cron Schedule**, set:
   ```
   */5 13-20 * * 1-5
   ```
   This runs every 5 minutes, Mon–Fri, covering 9am–4pm ET (UTC-4 summer).
   For winter (EST, UTC-5) use `*/5 14-21 * * 1-5`.
   The app also checks market hours internally, so running slightly outside
   the window is harmless — it just logs "Market is closed" and exits.

### 3. View logs

Railway → your service → **Deploy Logs**. A clean run looks like:

```
2026-06-02 14:30:00  INFO      === Stock Alert Run ===
2026-06-02 14:30:00  INFO      Market is open.
2026-06-02 14:30:00  INFO      Loaded 2 finding(s) from bot_findings.jsonl
2026-06-02 14:30:00  INFO      Watching 1 bot finding(s): AMD
2026-06-02 14:30:01  INFO      Fetching quotes for: SOXX, NVDA, NLR, JEPI, IDRV, SPY, GOOG, AMD
2026-06-02 14:30:02  INFO        SOXX    price=599.00  open=585.84
...
2026-06-02 14:30:03  INFO      0 alert(s) before cooldown.
2026-06-02 14:30:03  INFO      Nothing to send.
```

---

## Project structure

```
stock-alerts/
├── main.py                # entry point — runs on cron, orchestrates everything
├── config.py              # loads NTFY_TOPIC from env, fails loud if missing
├── requirements.txt       # yfinance, requests, python-dotenv, tzdata
├── bot_findings.jsonl     # agent appends picks here; never edit existing lines
├── .env                   # your ntfy topic (gitignored)
├── .env.example           # template
├── .gitignore
├── README.md
├── stocks/
│   ├── portfolio.py       # YOUR tickers, buy prices, sell targets, stop-losses
│   ├── watcher.py         # fetches current price + daily open via yfinance
│   └── findings.py        # loads + validates bot_findings.jsonl
└── alerts/
    ├── rules.py           # evaluates quotes against portfolio + findings rules
    └── sms.py             # sends push notifications via ntfy.sh
```

**Runtime files (gitignored, created automatically):**

| File | Purpose |
|---|---|
| `.env` | Your ntfy topic secret |
| `.cooldowns.json` | Tracks last-sent time per ticker+alert-type |
| `.seen_findings.json` | Tracks which bot picks have been announced |
