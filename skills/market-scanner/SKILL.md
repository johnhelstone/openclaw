---
name: market-scanner
description: "Scan financial markets for DEGIRO trade opportunities using technical analysis (RSI, MACD, Moving Averages, Bollinger Bands). Monitors AEX, S&P 500, and commodities (Gold, Oil, Silver, Copper). Use when: user asks for market scan, trade recommendations, investment ideas, buy/sell signals, portfolio picks, DEGIRO opportunities, or daily market analysis. Can run a live scan or a full 2-year backtest. Schedules daily at 08:00 Amsterdam time on weekdays. NOT for: crypto-only trading, options, leveraged products, or non-DEGIRO platforms."
metadata:
  {
    "openclaw":
      {
        "emoji": "📈",
        "requires": { "bins": ["python3"] },
      },
  }
---

# Market Scanner for DEGIRO

Daily financial market scanner with technical analysis signals and trade recommendations for the DEGIRO platform. Monitors AEX (Amsterdam), S&P 500 picks, and commodities using free Yahoo Finance data — no API key required.

## When to Use

Use this skill when the user asks:
- "Scan the markets" / "Market scan" / "Markt scannen"
- "What should I buy today on DEGIRO?"
- "Give me trade recommendations"
- "Best stocks this week"
- "Is [ticker] a buy or sell?"
- "Run a backtest on the strategy"
- "Set up daily market alerts"

## Quick Start

### Run a Live Market Scan

```bash
# Install dependencies (first time only)
pip install -r {baseDir}/scripts/requirements.txt -q

# Full scan (AEX + US + Commodities)
python {baseDir}/scripts/scanner.py

# AEX only
python {baseDir}/scripts/scanner.py --watchlist aex

# Show top 10 picks
python {baseDir}/scripts/scanner.py --top 10

# Lower threshold to see more signals
python {baseDir}/scripts/scanner.py --min-score 0.5

# Machine-readable JSON output
python {baseDir}/scripts/scanner.py --json
```

### Run a Backtest

```bash
# 2-year backtest with €10,000 starting capital
python {baseDir}/scripts/backtest.py

# Custom parameters
python {baseDir}/scripts/backtest.py --period 1y --capital 5000 --stop-loss 0.07 --take-profit 0.20

# AEX-only backtest
python {baseDir}/scripts/backtest.py --watchlist aex --period 2y
```

## Watchlist

| Group | Symbols |
|---|---|
| AEX | ASML.AS, HEIA.AS, PHIA.AS, INGA.AS, ABN.AS, SHEL.AS, UNA.AS, ADYEN.AS |
| US | AAPL, MSFT, NVDA, GOOGL, AMZN, META, JPM |
| Commodities | GC=F (Gold), CL=F (Oil), SI=F (Silver), HG=F (Copper) |

## Scanner Options

| Flag | Default | Description |
|---|---|---|
| `--watchlist` | `all` | `all`, `aex`, `us`, or `commodities` |
| `--top` | `5` | Number of top picks to show |
| `--min-score` | `1.0` | Minimum signal score to include (0–3 scale) |
| `--json` | off | Output machine-readable JSON |

## Backtest Options

| Flag | Default | Description |
|---|---|---|
| `--period` | `2y` | Historical period: `1y` or `2y` |
| `--capital` | `10000` | Starting capital in EUR |
| `--stop-loss` | `0.05` | Stop-loss threshold (5%) |
| `--take-profit` | `0.15` | Take-profit threshold (15%) |
| `--watchlist` | `all` | Same as scanner |

## Signal Scoring

Each symbol receives a score from −3 to +3 based on:

| Signal | Score |
|---|---|
| RSI 30–50 (recovering from oversold) | +1.0 |
| RSI < 30 (strongly oversold) | +0.5 |
| RSI > 70 (overbought) | −1.0 |
| Price above SMA50 | +0.5 |
| Price above SMA200 | +0.5 |
| MACD bullish crossover | +1.0 |
| MACD bearish crossover | −1.0 |
| Price near lower Bollinger Band (bottom 2%) | +0.5 |
| Price near upper Bollinger Band (top 2%) | −0.5 |

**Score thresholds**: ≥2.0 = STRONG BUY · ≥1.0 = BUY · 0 to 1 = NEUTRAL · <0 = AVOID

## Setting Up Daily Cron (via cron-tool)

To get automated daily market scans at 08:00 Amsterdam time (weekdays only):

```
Use the cron tool to schedule:
- Schedule: cron expression "0 8 * * 1-5" with timezone "Europe/Amsterdam"
- Payload kind: agentTurn
- Message: "Run market scanner: python {baseDir}/scripts/scanner.py and summarize the top 5 DEGIRO trade recommendations"
- Session: isolated
- Delivery: announce to main channel
```

## Output Format

```
=== MARKET SCANNER — 2026-04-08 08:00 AMS ===

BUY SIGNALS (Top 5)
1. ASML.AS   Score: +2.5  RSI: 38  Price: 812.40   SMA50: above  MACD: bullish  -> STRONG BUY
2. GC=F      Score: +2.0  RSI: 44  Price: 2340.10  SMA50: above  MACD: bullish  -> BUY
...

AVOID / SELL SIGNALS
1. META      Score: -1.5  RSI: 74  MACD: bearish  -> OVERBOUGHT

Market Summary: 3 BUY | 2 AVOID | 12 NEUTRAL
DEGIRO: Execute BUY orders at market open (09:00 AMS for AEX, 15:30 AMS for US). Use limit orders +/-0.5%.
```

## DEGIRO Notes

- AEX stocks trade on Euronext Amsterdam: 09:00–17:30 AMS
- US stocks trade 15:30–22:00 AMS (NYSE/NASDAQ)
- Tickers on DEGIRO use suffix `.AS` for AEX stocks (e.g. ASML.AS)
- Use limit orders to avoid slippage; set 0.5% above ask for buys
- See [references/degiro.md](references/degiro.md) for full DEGIRO platform guide

## Strategy Reference

See [references/strategy.md](references/strategy.md) for the full strategy explanation, indicator rationale, and risk management rules.

## Data Source

Yahoo Finance (free, no API key required). Data fetched via the `yfinance` Python library. Daily OHLCV data, up to 2 years history.
