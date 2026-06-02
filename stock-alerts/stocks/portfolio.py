# ============================================================
# YOUR PORTFOLIO — this is the file you'll edit most often.
# Find tickers at finance.yahoo.com (e.g. BRK-B, not BRK.B).
# Targets are based on current prices as of June 2025 —
# adjust sell_target and stop_loss to match your own thesis.
# ============================================================

# Stocks / ETFs you currently own.
# buy_price  : your average cost basis (used to show % gain/loss in alerts)
# sell_target: alert fires when price >= this
# stop_loss  : alert fires when price <= this
OWNED = [
    {
        "ticker": "SOXX",       # iShares Semiconductor ETF
        "buy_price": 214.05,    # current ~$599, 52w range $207–$599
        "sell_target": 680.00,  # +14% from current, new breakout territory
        "stop_loss": 530.00,    # -11% from current, below recent consolidation
    },
    {
        "ticker": "NVDA",       # Nvidia
        "buy_price": 96.81,     # current ~$223, 52w range $138–$237
        "sell_target": 260.00,  # +17% from current, above 52w high of $237
        "stop_loss": 190.00,    # -15% from current, meaningful support
    },
    {
        "ticker": "NLR",        # VanEck Uranium + Nuclear ETF
        "buy_price": 145.37,    # current ~$137 (slightly underwater), 52w range $97–$168
        "sell_target": 165.00,  # +20% from current, just below 52w high of $168
        "stop_loss": 120.00,    # -13% from current
    },
    {
        "ticker": "JEPI",       # JPMorgan Equity Premium Income ETF (income/dividend hold)
        "buy_price": 56.77,     # current ~$55, 52w range $55–$60
        "sell_target": 63.00,   # +14% from current, above 52w high of $60
        "stop_loss": 50.00,     # -10% from current
    },
    {
        "ticker": "IDRV",       # iShares Self-Driving EV & Tech ETF
        "buy_price": 31.18,     # current ~$45, 52w range $29–$46 (at all-time high)
        "sell_target": 56.00,   # +23% from current
        "stop_loss": 39.00,     # -14% from current
    },
    {
        "ticker": "SPY",        # S&P 500 ETF
        "buy_price": 526.89,    # current ~$759, 52w range $591–$760 (at all-time high)
        "sell_target": 880.00,  # +16% from current
        "stop_loss": 680.00,    # -10% from current
    },
    {
        "ticker": "GOOG",       # Alphabet / Google
        "buy_price": 148.82,    # current ~$362, 52w range $163–$404
        "sell_target": 420.00,  # +16% from current, near 52w high of $404
        "stop_loss": 310.00,    # -14% from current
    },
]

# Stocks you're watching to buy on a dip.
# buy_target: alert fires when price <= this
# max_buy   : your upper limit — shown in the alert for reference
WATCHLIST = [
    # Add tickers you want to buy here, e.g.:
    # {
    #     "ticker": "MSFT",
    #     "buy_target": 380.00,
    #     "max_buy": 400.00,
    # },
]

# Alert behaviour (applies to all stocks above)
ALERT_RULES = {
    # Fire an intraday alert if price moves +/- this % from today's open
    "intraday_move_pct": 5.0,
    # Don't repeat the same alert for the same ticker+type within this window
    "cooldown_minutes": 60,
}
