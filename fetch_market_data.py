#!/usr/bin/env python3
"""
NEXUS COMMAND — Market Data Fetcher
Uses yfinance — handles Yahoo Finance auth internally, not blocked on GH Actions.
One batch download for history + lightweight fast_info per symbol for current price.
"""

import json, time, sys
import yfinance as yf
from datetime import datetime, timezone

SYMBOLS = {
    "SPY":   {"name": "S&P 500 ETF",        "sector": "Index",   "type": "etf"},
    "QQQ":   {"name": "NASDAQ-100 ETF",      "sector": "Index",   "type": "etf"},
    "DIA":   {"name": "Dow Jones ETF",       "sector": "Index",   "type": "etf"},
    "IWM":   {"name": "Russell 2000 ETF",    "sector": "Index",   "type": "etf"},
    "AAPL":  {"name": "Apple Inc.",          "sector": "Tech",    "type": "stock"},
    "NVDA":  {"name": "NVIDIA Corp.",        "sector": "Tech",    "type": "stock"},
    "MSFT":  {"name": "Microsoft Corp.",     "sector": "Tech",    "type": "stock"},
    "AMZN":  {"name": "Amazon.com",          "sector": "Tech",    "type": "stock"},
    "META":  {"name": "Meta Platforms",      "sector": "Tech",    "type": "stock"},
    "GOOGL": {"name": "Alphabet Inc.",       "sector": "Tech",    "type": "stock"},
    "TSLA":  {"name": "Tesla Inc.",          "sector": "Auto/EV", "type": "stock"},
    "BRK-B": {"name": "Berkshire Hathaway",  "sector": "Finance", "type": "stock"},
}


def build_history(close_series, n_days):
    result = []
    for ts, price in close_series.items():
        try:
            float_price = float(price)
            if float_price != float_price:  # NaN check
                continue
        except (TypeError, ValueError):
            continue
        result.append({"date": str(ts)[:10], "close": round(float_price, 2)})
    return result[-n_days:]


def main():
    print(f"Fetching at {datetime.now(timezone.utc).isoformat()} | yfinance {yf.__version__}")

    sym_list = list(SYMBOLS.keys())

    # ── Single batch download: 35 days of history for all symbols ──────────────
    # One network request instead of 12 — much less likely to be rate-limited
    print(f"Batch downloading 35d history for {len(sym_list)} symbols...")
    try:
        bulk = yf.download(
            sym_list,
            period="35d",
            interval="1d",
            auto_adjust=True,
            progress=False,
            group_by="ticker",
        )
    except Exception as e:
        print(f"Batch download failed: {e}")
        sys.exit(1)

    print("Batch download complete. Fetching live quotes...")
    quotes = {}

    for symbol, meta in SYMBOLS.items():
        try:
            # ── Current price ─────────────────────────────────────────────────
            fi = yf.Ticker(symbol).fast_info
            current_price = fi.last_price
            prev_close    = fi.previous_close

            if current_price is None or prev_close is None:
                print(f"  ⚠ {symbol}: no price data")
                continue

            current_price = round(float(current_price), 2)
            prev_close    = round(float(prev_close), 2)
            change        = round(current_price - prev_close, 2)
            change_pct    = round((change / prev_close) * 100, 2) if prev_close else 0

            # ── History from batch download ───────────────────────────────────
            # Multi-symbol download produces (ticker, field) multi-level columns
            try:
                close_col = bulk[symbol]["Close"].dropna()
                history_30d = build_history(close_col, 30)
                history_7d  = history_30d[-7:]
            except Exception as he:
                print(f"  ⚠ {symbol}: history error ({he}), using empty")
                history_30d, history_7d = [], []

            # ── Market state ──────────────────────────────────────────────────
            try:
                tz = fi.timezone  # e.g. "America/New_York"
                market_state = "REGULAR" if tz else "CLOSED"
            except Exception:
                market_state = "CLOSED"

            quotes[symbol] = {
                "symbol":      symbol,
                "name":        meta["name"],
                "sector":      meta["sector"],
                "type":        meta["type"],
                "price":       current_price,
                "prev_close":  prev_close,
                "change":      change,
                "change_pct":  change_pct,
                "market_state": market_state,
                "currency":    "USD",
                "history_30d": history_30d,
                "history_7d":  history_7d,
            }
            print(f"  ✅ {symbol}: ${current_price} ({change_pct:+.2f}%) | {len(history_30d)}d history")

        except Exception as e:
            print(f"  ❌ {symbol}: {e}")

        time.sleep(0.25)  # gentle pacing between fast_info calls

    if not quotes:
        print("FATAL: No symbols fetched.")
        sys.exit(1)

    output = {
        "generated_at":       datetime.now(timezone.utc).isoformat(),
        "generated_at_unix":  int(time.time()),
        "market_state":       quotes.get("SPY", {}).get("market_state", "CLOSED"),
        "quotes":             quotes,
        "symbols_count":      len(quotes),
    }

    with open("market.json", "w") as f:
        json.dump(output, f, separators=(",", ":"))

    print(f"\n✅ market.json written: {len(quotes)}/{len(SYMBOLS)} symbols")
    if len(quotes) < len(SYMBOLS) // 2:
        print("WARNING: fewer than half of symbols fetched")
        sys.exit(1)


if __name__ == "__main__":
    main()
