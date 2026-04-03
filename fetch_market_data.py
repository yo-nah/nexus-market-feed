#!/usr/bin/env python3
"""
NEXUS COMMAND — Market Data Fetcher
Fetches live stock/ETF/index data from Yahoo Finance and writes market.json.
Committed to the repo and served via raw.githubusercontent.com (CORS-enabled).
"""

import json
import time
import random
import requests
from datetime import datetime, timezone

SYMBOLS = {
    # Index ETFs
    "SPY":  {"name": "S&P 500 ETF",        "sector": "Index",    "type": "etf"},
    "QQQ":  {"name": "NASDAQ-100 ETF",      "sector": "Index",    "type": "etf"},
    "DIA":  {"name": "Dow Jones ETF",       "sector": "Index",    "type": "etf"},
    "IWM":  {"name": "Russell 2000 ETF",    "sector": "Index",    "type": "etf"},
    # Mega-cap equities
    "AAPL": {"name": "Apple Inc.",          "sector": "Tech",     "type": "stock"},
    "NVDA": {"name": "NVIDIA Corp.",        "sector": "Tech",     "type": "stock"},
    "MSFT": {"name": "Microsoft Corp.",     "sector": "Tech",     "type": "stock"},
    "AMZN": {"name": "Amazon.com",          "sector": "Tech",     "type": "stock"},
    "META": {"name": "Meta Platforms",      "sector": "Tech",     "type": "stock"},
    "GOOGL":{"name": "Alphabet Inc.",       "sector": "Tech",     "type": "stock"},
    "TSLA": {"name": "Tesla Inc.",          "sector": "Auto/EV",  "type": "stock"},
    "BRK-B":{"name": "Berkshire Hathaway",  "sector": "Finance",  "type": "stock"},
}

UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
]

def get_session() -> requests.Session:
    """Create a session that first visits Yahoo Finance to get cookies/crumb."""
    session = requests.Session()
    ua = random.choice(UA_LIST)
    session.headers.update({
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    })
    # Visit Yahoo Finance home to get cookies
    try:
        session.get("https://finance.yahoo.com", timeout=10)
        time.sleep(1)
        # Get crumb
        crumb_r = session.get("https://query1.finance.yahoo.com/v1/test/getcrumb", timeout=10)
        crumb = crumb_r.text.strip()
        if crumb and len(crumb) > 3:
            session.params = {"crumb": crumb}  # type: ignore
            print(f"  Got crumb: {crumb[:8]}...")
    except Exception as e:
        print(f"  Warning: crumb fetch failed: {e}")
    return session


def fetch_quote(session: requests.Session, symbol: str) -> dict | None:
    """Fetch 30-day daily history + current quote from Yahoo Finance."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {
        "range": "30d",
        "interval": "1d",
        "includePrePost": "false",
        "events": "div,splits",
    }
    session.headers["Referer"] = f"https://finance.yahoo.com/quote/{symbol}/"
    
    for attempt in range(3):
        try:
            r = session.get(url, params=params, timeout=12)
            if r.status_code == 429:
                wait = 5 + attempt * 3
                print(f"    Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            r.raise_for_status()
            data = r.json()
            result = data["chart"]["result"][0]
            meta = result["meta"]
            timestamps = result.get("timestamp", [])
            quotes = result["indicators"]["quote"][0]
            closes = quotes.get("close", [])

            history = []
            for ts, close in zip(timestamps, closes):
                if close is not None:
                    history.append({
                        "date": datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"),
                        "close": round(float(close), 2),
                    })

            current_price = meta.get("regularMarketPrice")
            prev_close = meta.get("chartPreviousClose") or meta.get("previousClose")

            if not current_price and closes:
                current_price = next((c for c in reversed(closes) if c is not None), None)
            if not prev_close and len(history) >= 2:
                prev_close = history[-2]["close"]

            if current_price is None:
                return None

            current_price = float(current_price)
            prev_close = float(prev_close) if prev_close else current_price
            change = round(current_price - prev_close, 2)
            change_pct = round((change / prev_close) * 100, 2) if prev_close else 0

            return {
                "symbol": symbol,
                "name": SYMBOLS[symbol]["name"],
                "sector": SYMBOLS[symbol]["sector"],
                "type": SYMBOLS[symbol]["type"],
                "price": round(current_price, 2),
                "prev_close": round(prev_close, 2),
                "change": change,
                "change_pct": change_pct,
                "volume": meta.get("regularMarketVolume"),
                "market_state": meta.get("marketState", "CLOSED"),
                "currency": meta.get("currency", "USD"),
                "history_30d": history,
                "history_7d": history[-7:] if len(history) >= 7 else history,
            }
        except Exception as e:
            print(f"    Attempt {attempt+1} failed: {e}")
            time.sleep(2)
    return None


def main():
    print(f"Fetching market data at {datetime.now(timezone.utc).isoformat()}")
    session = get_session()
    quotes = {}

    for symbol in SYMBOLS:
        print(f"  Fetching {symbol}...")
        quote = fetch_quote(session, symbol)
        if quote:
            quotes[symbol] = quote
            print(f"  ✅ {symbol}: ${quote['price']} ({quote['change_pct']:+.2f}%)")
        else:
            print(f"  ❌ {symbol}: failed")
        time.sleep(random.uniform(0.8, 1.5))

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_at_unix": int(time.time()),
        "market_state": quotes.get("SPY", {}).get("market_state", "CLOSED"),
        "quotes": quotes,
        "symbols_count": len(quotes),
    }

    with open("market.json", "w") as f:
        json.dump(output, f, separators=(",", ":"))

    print(f"\n✅ Written market.json with {len(quotes)}/{len(SYMBOLS)} symbols")
    if len(quotes) < len(SYMBOLS) // 2:
        print("⚠️  WARNING: Less than half of symbols fetched — check Yahoo Finance access")
        exit(1)


if __name__ == "__main__":
    main()
