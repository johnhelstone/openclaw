# DEGIRO Platform Reference

## Overview

DEGIRO is a European online broker headquartered in the Netherlands. It offers access to stocks, ETFs, bonds, options, futures, and warrants across 50+ exchanges. Known for low commissions and a clean mobile app.

---

## Trading Hours

| Market | Exchange | Hours (Amsterdam) |
|---|---|---|
| AEX (Amsterdam) | Euronext Amsterdam | 09:00 – 17:30 |
| Frankfurt | Xetra | 09:00 – 17:30 |
| London | LSE | 09:00 – 17:30 |
| New York | NYSE / NASDAQ | 15:30 – 22:00 |
| Commodities (Futures) | CME / COMEX | Various (24h nearly) |

The scanner runs at **08:00 Amsterdam time** — 1 hour before AEX opens, giving time to review signals and place limit orders before the open.

---

## Ticker Suffixes on DEGIRO

| Exchange | Suffix | Example |
|---|---|---|
| Euronext Amsterdam (AEX) | `.AS` | ASML.AS |
| Euronext Brussels | `.BR` | UCB.BR |
| London Stock Exchange | `.L` | SHEL.L |
| Frankfurt / Xetra | `.DE` | SAP.DE |
| US (NYSE/NASDAQ) | none | AAPL |
| Commodities Futures | `=F` | GC=F (Gold) |

> Note: Yahoo Finance tickers use these suffixes. On DEGIRO itself, search by company name or ISIN.

---

## Commission Structure (as of 2024)

| Asset Class | DEGIRO Commission |
|---|---|
| AEX stocks (Euronext Amsterdam) | €0 + €0 exchange fee |
| Other Euronext markets | €0 + €0 |
| US stocks (NYSE/NASDAQ) | $0 + $0 |
| German stocks (Xetra) | €3.90 + €0 |
| ETFs (core selection) | €0 |
| Other stocks/ETFs | €2.00 + 0.026% (min €0) |
| Options | €0.75/contract |

*Verify current rates at degiro.nl/tarieven — rates can change.*

---

## Order Types on DEGIRO

### Market Order
- Executes immediately at best available price
- Use only for highly liquid AEX stocks in normal market conditions
- Risk: slippage during volatile opens

### Limit Order (Recommended)
- Executes only at your specified price or better
- Prevents slippage
- For BUY signals: set limit **0.5% above** last close price
- For SELL signals: set limit **0.5% below** last close price
- Orders can be GTC (Good Till Cancelled) or Day

### Stop Loss Order
- Triggers a market sell when price drops to your stop level
- Set stop-loss at **−5% from entry price**
- Example: bought ASML at €800 → set stop at €760

---

## Finding DEGIRO Product IDs

DEGIRO uses internal product IDs. To find a stock:
1. Log in to DEGIRO app or web
2. Use the search bar with the company name (e.g. "ASML")
3. Select the correct exchange (e.g. Euronext Amsterdam)
4. The URL will show the product ID: `app.degiro.com/trader/#/products/detail/{ID}`

---

## AEX Watchlist — ISIN Reference

| Ticker | Company | ISIN |
|---|---|---|
| ASML.AS | ASML Holding | NL0010273215 |
| HEIA.AS | Heineken | NL0000009165 |
| PHIA.AS | Philips | NL0000009538 |
| INGA.AS | ING Groep | NL0011821202 |
| ABN.AS | ABN AMRO | NL0011540547 |
| SHEL.AS | Shell | GB00BP6MXD84 |
| UNA.AS | Unilever | GB00B10RZP78 |
| ADYEN.AS | Adyen | NL0012969182 |
| NN.AS | NN Group | NL0010773842 |
| AKZA.AS | Akzo Nobel | NL0013267909 |

---

## Commodities on DEGIRO

DEGIRO allows trading commodity ETPs and some futures products. Direct futures (GC=F, CL=F) may require a derivatives account.

**Commodity ETPs (tradeable on DEGIRO):**

| Commodity | ETP Example | ISIN |
|---|---|---|
| Gold | Invesco Physical Gold (SGLD) | IE00B579F325 |
| Silver | WisdomTree Physical Silver | JE00B1VS3770 |
| Oil | WisdomTree Brent Crude | JE00B78CGV99 |
| Copper | WisdomTree Copper | JE00B2QPKH16 |

Use these ETPs as DEGIRO-tradeable proxies for the commodity futures signals.

---

## Executing Trades Based on Scanner Signals

### Morning Routine (08:00 AMS)
1. Review scanner output (daily cron delivers it via chat)
2. Check signal list for STRONG BUY and BUY signals
3. Log into DEGIRO app
4. Place **limit orders** at last close price +0.5% for BUY signals
5. Set corresponding **stop-loss orders** at −5% from entry

### Risk Sizing Example (€10,000 portfolio)
- Max 5 positions → €2,000 per position
- Stop-loss at 5% → max loss per position: €100
- Total portfolio stop: never risk more than 2% of total capital per trade

### Checklist Before Placing Order
- [ ] Signal score ≥ 1.0
- [ ] No earnings announcement within 5 days (check DEGIRO news)
- [ ] Market is open or order is for market open
- [ ] Stop-loss order placed simultaneously
- [ ] Position size within limits

---

## Unofficial DEGIRO API (Advanced)

DEGIRO does not provide an official public API. An unofficial Python library exists for automation:

```bash
pip install degiro-connector
```

Repository: `https://github.com/Chavithra/degiro-connector`

Features: login, portfolio view, order placement, order history, real-time quotes.

**Warning**: Use of unofficial APIs may violate DEGIRO terms of service. Always review current ToS before automating order placement. Use only for personal, non-commercial purposes.

---

## Disclaimer

This tool provides educational market analysis only. It is not financial advice. Past performance does not guarantee future results. Trading involves risk of loss. Always do your own research before investing. DEGIRO commission rates and features may change — verify at degiro.nl.
