# nexus-market-feed

Automated market data feed for **NEXUS COMMAND** — a live AI capability demonstration platform.

A GitHub Actions workflow fetches live stock/ETF quotes from Yahoo Finance every 5 minutes during market hours and commits updated `market.json` to this repo.

The JSON file is served via `raw.githubusercontent.com` which includes CORS headers, making it directly consumable from any browser-based app.

## Data Endpoint

```
https://raw.githubusercontent.com/yo-nah/nexus-market-feed/main/market.json
```

## Symbols Tracked

| Symbol | Name | Type |
|--------|------|------|
| SPY | S&P 500 ETF | Index ETF |
| QQQ | NASDAQ-100 ETF | Index ETF |
| DIA | Dow Jones ETF | Index ETF |
| IWM | Russell 2000 ETF | Index ETF |
| AAPL | Apple Inc. | Stock |
| NVDA | NVIDIA Corp. | Stock |
| MSFT | Microsoft Corp. | Stock |
| AMZN | Amazon.com | Stock |
| META | Meta Platforms | Stock |
| GOOGL | Alphabet Inc. | Stock |
| TSLA | Tesla Inc. | Stock |
| BRK-B | Berkshire Hathaway | Stock |

## Update Frequency

- **Every 5 minutes** during market hours (Mon–Fri, 9:30am–4:00pm ET)
- **Every 15 minutes** outside market hours

## Schema

```json
{
  "generated_at": "ISO8601 timestamp",
  "generated_at_unix": 1234567890,
  "market_state": "REGULAR|PRE|POST|CLOSED",
  "symbols_count": 12,
  "quotes": {
    "SPY": {
      "symbol": "SPY",
      "name": "S&P 500 ETF",
      "sector": "Index",
      "type": "etf",
      "price": 524.60,
      "prev_close": 552.10,
      "change": -27.50,
      "change_pct": -4.98,
      "volume": 123456789,
      "market_state": "CLOSED",
      "history_30d": [{"date": "2026-03-01", "close": 540.0}, ...],
      "history_7d": [{"date": "2026-03-27", "close": 535.0}, ...]
    }
  }
}
```
