import logging
import yfinance as yf

logger = logging.getLogger(__name__)


def fetch_quotes(tickers: list[str]) -> dict[str, dict]:
    """
    Fetch current price and today's open for each ticker via yfinance.

    Returns a dict keyed by ticker:
        { "price": float, "open": float }

    Tickers that fail are omitted and logged as warnings.
    """
    if not tickers:
        return {}

    quotes = {}
    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).fast_info
            price = info.last_price
            open_price = info.open
            if price is None or open_price is None:
                logger.warning("No price data for %s — skipping", ticker)
                continue
            quotes[ticker] = {"price": float(price), "open": float(open_price)}
            logger.info("  %-6s  price=%.2f  open=%.2f", ticker, price, open_price)
        except Exception as exc:
            logger.warning("Failed to fetch %s: %s", ticker, exc)

    return quotes


if __name__ == "__main__":
    # Quick sanity check: python -m stocks.watcher
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
    from stocks.portfolio import OWNED, WATCHLIST

    tickers = [s["ticker"] for s in OWNED] + [s["ticker"] for s in WATCHLIST]
    tickers = list(dict.fromkeys(tickers))
    print(f"Fetching quotes for: {', '.join(tickers)}\n")
    result = fetch_quotes(tickers)
    print("\nResult:")
    for t, q in result.items():
        print(f"  {t}: ${q['price']:.2f}  (open ${q['open']:.2f})")
