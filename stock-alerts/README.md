# Stock Price Alerts

Monitors your portfolio and watchlist every ~10 minutes during US market hours and texts you when prices hit your targets or move sharply intraday.

## What gets texted

| Situation | Alert type |
|---|---|
| Owned stock reaches your sell target | `[SELL TARGET]` |
| Owned stock hits your stop-loss | `[STOP LOSS]` |
| Any owned stock moves ±5% from open | `[UP +X%]` / `[DOWN -X%]` |
| Watchlist stock drops to your buy target | `[BUY TARGET]` |
| Watchlist stock drops ≥5% from open | `[WATCHLIST DIP]` |

A 60-minute cooldown prevents repeat texts for the same ticker+type. Both thresholds are configurable in `stocks/portfolio.py`.

---

## Local setup

### 1. Prerequisites

- Python 3.11+
- A [Twilio account](https://www.twilio.com/try-twilio) (free trial is fine to start)

### 2. Install dependencies

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure your portfolio

Edit `stocks/portfolio.py` — this is the only file you touch day-to-day:

- `OWNED` — stocks you hold: add your buy price, sell target, and stop-loss
- `WATCHLIST` — stocks you're watching: add the price you'd buy at
- `ALERT_RULES` — tweak the intraday move threshold (default 5%) and cooldown

### 4. Set up Twilio (read this carefully — it's a 5-minute job)

#### Sign up and find your credentials

1. Go to [twilio.com/try-twilio](https://www.twilio.com/try-twilio) and create a free account.
   New accounts get **~$15 trial credit** — enough for thousands of SMS messages.

2. After verifying your email, you land in the **Twilio Console**.
   Under **Account Info** (bottom-left) you'll see:
   - **Account SID** — starts with `AC...` — this is your username
   - **Auth Token** — click the 👁 icon to reveal it — this is your password

3. In the Console, go to **Phone Numbers → Manage → Buy a number**.
   Search for a US number, click Buy. It costs ~$1/month (covered by trial credit).
   Your trial credit also covers this charge.

#### Trial-mode limitations

While you're on a free trial:
- Twilio can **only text numbers you've explicitly verified**. To verify your phone:
  Go to **Verify Callers** in the Console and add your number.
- Every text will be prefixed with *"Sent from your Twilio trial account"*.
- This is fine for personal use. If you ever want to remove the prefix or text unverified numbers, upgrade to a paid account (~$20/month minimum, no contract).

#### A2P 10DLC — do you need it?

Only if you plan to send bulk messages to many people. For a personal app texting **only your own verified number**, you don't need it. Skip it.

#### Copy and fill in `.env`

```bash
cp .env.example .env
```

Open `.env` and fill in all four values:

```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_FROM_NUMBER=+12025551234   # the number you bought
YOUR_PHONE_NUMBER=+12015550000    # YOUR cell phone (must be verified on trial)
```

Phone numbers must be in E.164 format: `+1` followed by 10 digits, no spaces or dashes.

---

## Verify each stage

### Stage 2 — confirm price fetching works

```bash
python -m stocks.watcher
```

Should print current price and today's open for AAPL, MSFT, NVDA, TSLA. If you see `No price data`, the market may be closed or yfinance is rate-limiting — try again in a moment.

### Stage 3 — confirm alert logic works (no SMS)

```bash
python -m alerts.rules
```

Prints which alerts **would** fire based on current prices. Since the example targets are set conservatively, you'll probably see "No alerts would fire" — that's correct. You can temporarily lower a `sell_target` in `portfolio.py` to test a trigger.

### Stage 4 — send a test SMS

Make sure `.env` is filled in, then:

```bash
python -m alerts.sms
```

You should receive a text within ~10 seconds: *"Stock-alerts test — Twilio is wired up correctly!"*

If it fails, check:
- Your Account SID and Auth Token are correct (no extra spaces)
- `YOUR_PHONE_NUMBER` is verified in the Twilio Console (trial accounts)
- The number format is `+1XXXXXXXXXX`

### Stage 5 — full run

```bash
python main.py
```

This checks market hours, fetches quotes, evaluates rules, applies cooldowns, and sends any alerts. Run it during market hours (Mon–Fri 9:30am–4pm ET). Outside those hours you'll see `Market is closed — exiting.`

---

## Deploying to Railway

### 1. Push to GitHub

```bash
git add .
git commit -m "Initial stock-alerts app"
git remote add origin https://github.com/YOUR_USERNAME/stock-alerts.git
git push -u origin main
```

Make sure `.env` and `.cooldowns.json` are in `.gitignore` (they already are).

### 2. Create a Railway project

1. Go to [railway.app](https://railway.app) and sign in with GitHub.
2. Click **New Project → Deploy from GitHub repo** and select `stock-alerts`.
3. Railway will auto-detect Python and deploy. Let it finish (it'll fail the first run — that's fine, we haven't set env vars yet).

### 3. Add your environment variables

In your Railway project, go to **Variables** and add all four:

```
TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN
TWILIO_FROM_NUMBER
YOUR_PHONE_NUMBER
```

### 4. Add the cron job

In Railway, go to **Settings → Cron** and add:

```
*/10 9-16 * * 1-5
```

This runs `python main.py` every 10 minutes, Mon–Fri, between 9am and 4pm UTC.

**Important:** Railway cron runs in UTC. US Eastern Time is UTC-4 (EDT, summer) or UTC-5 (EST, winter). The app itself checks market hours in ET using `zoneinfo`, so it's safe to run slightly outside the window — it'll just log "Market is closed" and exit cleanly. Adjust the cron hour range if you want to be precise:

- Summer (EDT, UTC-4): `*/10 13-20 * * 1-5`
- Winter (EST, UTC-5): `*/10 14-21 * * 1-5`

### 5. View logs

In Railway, click your service → **Deployments → Logs**. You'll see output like:

```
2024-01-15 14:30:00  INFO      === Stock Alert Run ===
2024-01-15 14:30:00  INFO      Market is open.
2024-01-15 14:30:01  INFO      Fetching quotes for: AAPL, MSFT, NVDA, TSLA
2024-01-15 14:30:02  INFO        AAPL    price=195.50  open=193.20
...
2024-01-15 14:30:03  INFO      2 alert(s) before cooldown.
2024-01-15 14:30:03  INFO      2 alert(s) after cooldown.
2024-01-15 14:30:04  INFO      Done. Cooldowns saved.
```

---

## Project structure

```
stock-alerts/
├── main.py              # entry point — run on cron
├── config.py            # loads and validates env vars
├── requirements.txt
├── .env.example         # copy to .env and fill in
├── .gitignore
├── README.md
├── stocks/
│   ├── portfolio.py     # YOUR tickers + price targets (edit this)
│   └── watcher.py       # fetches price + open via yfinance
└── alerts/
    ├── rules.py         # evaluates quotes against your rules
    └── sms.py           # sends texts via Twilio
```

`.cooldowns.json` is created automatically at runtime to track alert history between cron runs. It's gitignored.
