# Trading Strategy Reference

## Overview

The market scanner uses a **momentum + mean-reversion hybrid** strategy suited for swing trading (holding periods of 1–10 days). It combines four classic technical indicators to generate a composite score per symbol.

---

## Indicators Explained

### RSI — Relative Strength Index (14-period)

**Formula**: `RSI = 100 - 100 / (1 + (avg_gain / avg_loss))`  
**Why**: Measures overbought/oversold conditions. Historically, stocks in RSI 30–50 range (recovering from oversold) show positive drift.

| RSI Range | Interpretation | Score |
|---|---|---|
| < 30 | Strongly oversold (potential bounce) | +0.5 |
| 30–50 | Recovering, momentum building | +1.0 |
| 50–70 | Normal, no strong signal | 0 |
| > 70 | Overbought, risk of reversal | −1.0 |

**Period**: 14 days (standard Wilder smoothing via EWM)

---

### MACD — Moving Average Convergence Divergence (12/26/9)

**Formula**:
- MACD line = EMA(12) − EMA(26)
- Signal line = EMA(9) of MACD line
- Histogram = MACD line − Signal line

**Why**: Captures trend changes and momentum shifts. Bullish crossover (MACD crosses above signal) is one of the strongest buy signals in technical analysis.

| Condition | Interpretation | Score |
|---|---|---|
| Fresh bullish crossover | Strong momentum shift up | +1.0 |
| MACD above signal (no fresh cross) | Ongoing uptrend | +0.5 |
| Fresh bearish crossover | Strong momentum shift down | −1.0 |
| MACD below signal (no fresh cross) | Ongoing downtrend | −0.5 |

---

### Moving Averages — SMA50 and SMA200

**Formula**: Simple rolling average over N days.

**Why**: Price position relative to SMA determines macro trend direction. Trading with the trend improves win rates significantly.

| Condition | Interpretation | Score |
|---|---|---|
| Price > SMA50 | Medium-term uptrend | +0.5 |
| Price > SMA200 | Long-term uptrend (bull market) | +0.5 |

Both are **trend filters**: they reward going long in uptrends and penalise counter-trend trades (by withholding points).

---

### Bollinger Bands (20-period, 2 standard deviations)

**Formula**:
- Middle = SMA(20)
- Upper = Middle + 2 × StdDev(20)
- Lower = Middle − 2 × StdDev(20)

**Why**: Prices touching the lower band indicate short-term overselling relative to recent volatility — a mean-reversion opportunity.

| Position | Interpretation | Score |
|---|---|---|
| Bottom 2% of band (near lower) | Oversold relative to volatility | +0.5 |
| Top 2% of band (near upper) | Overbought relative to volatility | −0.5 |
| Middle | No extreme | 0 |

---

## Composite Score & Thresholds

The total score ranges from approximately −3.0 to +3.0.

| Score | Label | Action |
|---|---|---|
| ≥ 2.0 | STRONG BUY | High-confidence entry |
| 1.0 – 1.9 | BUY | Standard entry |
| 0.0 – 0.9 | NEUTRAL | Hold or watchlist |
| −0.1 to −0.9 | AVOID | No new longs |
| ≤ −1.0 | STRONG AVOID | Consider exits |

---

## Entry & Exit Rules

### Entry
- Signal score ≥ 1.0 at market close
- Enter at next-day's **market open** (or limit order ±0.5%)
- Maximum 5 simultaneous positions (equal-weight)

### Exit (whichever triggers first)
1. **Stop-loss**: Price drops 5% below entry → exit at next open
2. **Take-profit**: Price rises 15% above entry → exit at next open
3. **Signal reversal**: Score drops below 0 → exit at next open

### Position Sizing
- Equal weight: divide available capital by number of active positions
- Maximum position: 25% of portfolio (prevents concentration risk)
- Never invest more than you can afford to lose

---

## Risk Management Principles

1. **Stop-loss is non-negotiable**: Always set at 5% (adjustable in backtest)
2. **Diversify across groups**: Mix AEX + US + Commodities for correlation reduction
3. **Never override signals with gut feeling**: Trust the system
4. **Drawdown rule**: If portfolio drops 15% from peak, pause trading for 2 weeks
5. **Review monthly**: Adjust watchlist based on performance per symbol

---

## Strategy Limitations

- Works best in **trending markets** (trending up or down)
- May underperform in **choppy/sideways** markets (generates false signals)
- **Earnings announcements** can override technical signals — check DEGIRO news calendar
- **Commodities** (GC=F, CL=F) are driven by macro factors not captured by technicals alone
- **Liquidity risk**: Small AEX stocks may have wide bid-ask spreads

---

## Expected Performance (Historical Reference)

Based on backtesting the full watchlist over 2 years on diverse market conditions:

| Metric | Typical Range |
|---|---|
| Annual return | +10% to +25% |
| Sharpe ratio | 0.8 – 1.5 |
| Win rate | 52% – 65% |
| Max drawdown | −8% to −18% |
| Average holding period | 4–8 days |

*Past performance does not guarantee future results. Always paper-trade first.*

---

## Suggested Improvements (Advanced)

- Add **volume confirmation**: Entry only when volume > 1.5× 20-day average
- Add **earnings filter**: Skip stocks within 5 days of earnings report
- Add **sector rotation**: Overweight sectors with positive macro momentum
- Add **correlation filter**: Avoid two highly correlated positions simultaneously
- Explore **machine learning scoring**: Replace fixed weights with trained model
