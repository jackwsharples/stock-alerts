from stocks.portfolio import OWNED, WATCHLIST, ALERT_RULES


def _pct(current: float, reference: float) -> float:
    if reference == 0:
        return 0.0
    return (current - reference) / reference * 100


def evaluate(quotes: dict[str, dict]) -> list[dict]:
    """
    Evaluate fetched quotes against portfolio rules.

    Returns a list of alert dicts:
        { "ticker": str, "type": str, "message": str }

    Alert types:
        sell_target     — owned stock hit sell price
        stop_loss       — owned stock hit stop-loss
        intraday_up     — owned/watch stock up >= threshold from open
        intraday_down   — owned stock down >= threshold from open
        buy_target      — watchlist stock hit buy price
        watchlist_dip   — watchlist stock down >= threshold from open
    """
    threshold = ALERT_RULES.get("intraday_move_pct", 5.0)
    alerts = []

    for stock in OWNED:
        ticker = stock["ticker"]
        if ticker not in quotes:
            continue
        price = quotes[ticker]["price"]
        open_price = quotes[ticker]["open"]
        intraday = _pct(price, open_price)
        total = _pct(price, stock["buy_price"])

        if price >= stock["sell_target"]:
            alerts.append({
                "ticker": ticker,
                "type": "sell_target",
                "message": (
                    f"[SELL TARGET] {ticker} @ ${price:.2f} reached your sell target of "
                    f"${stock['sell_target']:.2f}. Total gain: {total:+.1f}%."
                ),
            })

        if price <= stock["stop_loss"]:
            alerts.append({
                "ticker": ticker,
                "type": "stop_loss",
                "message": (
                    f"[STOP LOSS] {ticker} @ ${price:.2f} hit your stop-loss of "
                    f"${stock['stop_loss']:.2f}. Total loss: {total:+.1f}%."
                ),
            })

        if intraday >= threshold:
            alerts.append({
                "ticker": ticker,
                "type": "intraday_up",
                "message": (
                    f"[UP {intraday:+.1f}%] {ticker} surged from ${open_price:.2f} "
                    f"to ${price:.2f} today."
                ),
            })

        if intraday <= -threshold:
            alerts.append({
                "ticker": ticker,
                "type": "intraday_down",
                "message": (
                    f"[DOWN {intraday:+.1f}%] {ticker} dropped from ${open_price:.2f} "
                    f"to ${price:.2f} today."
                ),
            })

    for stock in WATCHLIST:
        ticker = stock["ticker"]
        if ticker not in quotes:
            continue
        price = quotes[ticker]["price"]
        open_price = quotes[ticker]["open"]
        intraday = _pct(price, open_price)

        if price <= stock["buy_target"]:
            alerts.append({
                "ticker": ticker,
                "type": "buy_target",
                "message": (
                    f"[BUY TARGET] {ticker} @ ${price:.2f} hit your buy target of "
                    f"${stock['buy_target']:.2f} (your max: ${stock['max_buy']:.2f})."
                ),
            })

        if intraday <= -threshold:
            alerts.append({
                "ticker": ticker,
                "type": "watchlist_dip",
                "message": (
                    f"[WATCHLIST DIP {intraday:+.1f}%] {ticker} dropped from "
                    f"${open_price:.2f} to ${price:.2f}. Buy target: ${stock['buy_target']:.2f}."
                ),
            })

    return alerts


if __name__ == "__main__":
    # Dry-run: prints which alerts WOULD fire. No SMS sent.
    # Usage: python -m alerts.rules
    import logging
    from stocks.watcher import fetch_quotes
    from stocks.portfolio import OWNED, WATCHLIST

    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    tickers = list(dict.fromkeys(
        [s["ticker"] for s in OWNED] + [s["ticker"] for s in WATCHLIST]
    ))
    print(f"Fetching quotes for: {', '.join(tickers)}\n")
    quotes = fetch_quotes(tickers)

    alerts = evaluate(quotes)
    if alerts:
        print(f"\n{len(alerts)} alert(s) would fire:\n")
        for a in alerts:
            print(f"  [{a['type']}] {a['message']}")
    else:
        print("\nNo alerts would fire with current prices.")
