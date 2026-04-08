#!/usr/bin/env python3
"""
Market Scanner for DEGIRO — OpenClaw Skill
==========================================
Scans AEX, S&P 500 picks, and commodities using technical analysis.
Data source: Yahoo Finance (free, no API key required).

Usage:
    python scanner.py [--watchlist all|aex|us|commodities]
                      [--top N] [--min-score FLOAT] [--json]
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    import numpy as np
    import pandas as pd
    import yfinance as yf
except ImportError:
    print(
        "Missing dependencies. Run: pip install yfinance pandas numpy",
        file=sys.stderr,
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Watchlists
# ---------------------------------------------------------------------------

WATCHLIST_AEX = [
    "ASML.AS",   # ASML Holding
    "HEIA.AS",   # Heineken
    "PHIA.AS",   # Philips
    "INGA.AS",   # ING Groep
    "ABN.AS",    # ABN AMRO
    "SHEL.AS",   # Shell
    "UNA.AS",    # Unilever
    "ADYEN.AS",  # Adyen
    "NN.AS",     # NN Group
    "AKZA.AS",   # Akzo Nobel
]

WATCHLIST_US = [
    "AAPL",   # Apple
    "MSFT",   # Microsoft
    "NVDA",   # Nvidia
    "GOOGL",  # Alphabet
    "AMZN",   # Amazon
    "META",   # Meta
    "JPM",    # JPMorgan
    "BRK-B",  # Berkshire Hathaway
    "JNJ",    # Johnson & Johnson
    "XOM",    # ExxonMobil
]

WATCHLIST_COMMODITIES = [
    "GC=F",  # Gold Futures
    "CL=F",  # Crude Oil Futures
    "SI=F",  # Silver Futures
    "HG=F",  # Copper Futures
    "NG=F",  # Natural Gas Futures
]

WATCHLISTS: Dict[str, List[str]] = {
    "aex": WATCHLIST_AEX,
    "us": WATCHLIST_US,
    "commodities": WATCHLIST_COMMODITIES,
    "all": WATCHLIST_AEX + WATCHLIST_US + WATCHLIST_COMMODITIES,
}


# ---------------------------------------------------------------------------
# Technical indicators (pure pandas/numpy, no ta-lib dependency)
# ---------------------------------------------------------------------------

def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    return 100.0 - (100.0 / (1.0 + rs))


def compute_macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def compute_bollinger(
    close: pd.Series, period: int = 20, num_std: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    mid = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    return upper, mid, lower


def compute_sma(close: pd.Series, period: int) -> pd.Series:
    return close.rolling(period).mean()


# ---------------------------------------------------------------------------
# Signal dataclass
# ---------------------------------------------------------------------------

@dataclass
class Signal:
    symbol: str
    price: float
    score: float
    rsi: float
    macd_bullish: bool
    above_sma50: bool
    above_sma200: bool
    bb_position: str  # "lower", "middle", "upper"
    recommendation: str
    reasons: List[str]
    currency: str


def label_from_score(score: float) -> str:
    if score >= 2.0:
        return "STRONG BUY"
    if score >= 1.0:
        return "BUY"
    if score <= -1.5:
        return "STRONG AVOID"
    if score <= -0.5:
        return "AVOID"
    return "NEUTRAL"


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def analyse_symbol(symbol: str) -> Optional[Signal]:
    """Download data and compute signals for a single symbol."""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1y", interval="1d", auto_adjust=True)
        if df is None or len(df) < 60:
            return None
    except Exception:
        return None

    close = df["Close"].dropna()
    if len(close) < 60:
        return None

    price = float(close.iloc[-1])
    currency = "EUR" if symbol.endswith(".AS") else "USD"

    # RSI
    rsi_series = compute_rsi(close)
    rsi = float(rsi_series.iloc[-1]) if not rsi_series.isna().iloc[-1] else 50.0

    # MACD
    macd_line, signal_line, _ = compute_macd(close)
    macd_val = float(macd_line.iloc[-1]) if not macd_line.isna().iloc[-1] else 0.0
    sig_val = float(signal_line.iloc[-1]) if not signal_line.isna().iloc[-1] else 0.0
    macd_bullish = macd_val > sig_val
    # Detect crossover: yesterday bearish, today bullish (or vice versa)
    if len(macd_line) >= 2 and not macd_line.isna().iloc[-2]:
        prev_macd = float(macd_line.iloc[-2])
        prev_sig = float(signal_line.iloc[-2])
        fresh_cross_up = prev_macd <= prev_sig and macd_val > sig_val
        fresh_cross_down = prev_macd >= prev_sig and macd_val < sig_val
    else:
        fresh_cross_up = False
        fresh_cross_down = False

    # Moving averages
    sma50 = compute_sma(close, 50)
    sma200 = compute_sma(close, 200)
    above_sma50 = (
        not sma50.isna().iloc[-1] and price > float(sma50.iloc[-1])
    )
    above_sma200 = (
        not sma200.isna().iloc[-1] and price > float(sma200.iloc[-1])
    )

    # Bollinger Bands
    bb_upper, bb_mid, bb_lower = compute_bollinger(close)
    if bb_upper.isna().iloc[-1]:
        bb_pos = "middle"
    else:
        u = float(bb_upper.iloc[-1])
        lo = float(bb_lower.iloc[-1])
        band_range = u - lo if u != lo else 1.0
        pct = (price - lo) / band_range  # 0 = lower band, 1 = upper band
        if pct <= 0.02:
            bb_pos = "lower"
        elif pct >= 0.98:
            bb_pos = "upper"
        else:
            bb_pos = "middle"

    # --- Scoring ---
    score = 0.0
    reasons: List[str] = []

    # RSI signals
    if 30 <= rsi <= 50:
        score += 1.0
        reasons.append(f"RSI {rsi:.0f} recovering from oversold")
    elif rsi < 30:
        score += 0.5
        reasons.append(f"RSI {rsi:.0f} strongly oversold")
    elif rsi > 70:
        score -= 1.0
        reasons.append(f"RSI {rsi:.0f} overbought")

    # MACD signals (crossover gets extra weight)
    if fresh_cross_up:
        score += 1.0
        reasons.append("MACD fresh bullish crossover")
    elif macd_bullish:
        score += 0.5
        reasons.append("MACD bullish")

    if fresh_cross_down:
        score -= 1.0
        reasons.append("MACD fresh bearish crossover")
    elif not macd_bullish:
        score -= 0.5
        reasons.append("MACD bearish")

    # Trend filters
    if above_sma50:
        score += 0.5
        reasons.append("Price above SMA50 (uptrend)")
    else:
        reasons.append("Price below SMA50 (downtrend)")

    if above_sma200:
        score += 0.5
        reasons.append("Price above SMA200 (long-term uptrend)")
    else:
        reasons.append("Price below SMA200 (long-term downtrend)")

    # Bollinger Band position
    if bb_pos == "lower":
        score += 0.5
        reasons.append("Price at lower Bollinger Band (mean-reversion opportunity)")
    elif bb_pos == "upper":
        score -= 0.5
        reasons.append("Price at upper Bollinger Band (stretched)")

    return Signal(
        symbol=symbol,
        price=price,
        score=round(score, 2),
        rsi=round(rsi, 1),
        macd_bullish=macd_bullish,
        above_sma50=above_sma50,
        above_sma200=above_sma200,
        bb_position=bb_pos,
        recommendation=label_from_score(score),
        reasons=reasons,
        currency=currency,
    )


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def format_price(price: float, currency: str) -> str:
    symbol_map = {"EUR": "€", "USD": "$"}
    sym = symbol_map.get(currency, currency + " ")
    if price >= 1000:
        return f"{sym}{price:,.2f}"
    return f"{sym}{price:.2f}"


def print_text_report(signals: List[Signal], top_n: int, min_score: float) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"\n=== MARKET SCANNER — {now} ===\n")

    buys = [s for s in signals if s.score >= min_score]
    avoids = [s for s in signals if s.score < 0]
    neutral = [s for s in signals if 0 <= s.score < min_score]

    buys_sorted = sorted(buys, key=lambda s: s.score, reverse=True)[:top_n]
    avoids_sorted = sorted(avoids, key=lambda s: s.score)[:5]

    if buys_sorted:
        print(f"BUY SIGNALS (Top {len(buys_sorted)})")
        print("-" * 70)
        for i, s in enumerate(buys_sorted, 1):
            trend = "above SMA50" if s.above_sma50 else "below SMA50"
            macd_str = "bullish" if s.macd_bullish else "bearish"
            print(
                f"{i:2}. {s.symbol:<12} "
                f"Score: {s.score:+.1f}  "
                f"RSI: {s.rsi:.0f}  "
                f"Price: {format_price(s.price, s.currency):<12}  "
                f"Trend: {trend:<15}  "
                f"MACD: {macd_str:<8}  "
                f"-> {s.recommendation}"
            )
            for r in s.reasons[:3]:
                print(f"     • {r}")
            print()
    else:
        print("No BUY signals above threshold.\n")

    if avoids_sorted:
        print("AVOID / SELL SIGNALS")
        print("-" * 70)
        for s in avoids_sorted:
            macd_str = "bullish" if s.macd_bullish else "bearish"
            print(
                f"   {s.symbol:<12} "
                f"Score: {s.score:+.1f}  "
                f"RSI: {s.rsi:.0f}  "
                f"Price: {format_price(s.price, s.currency):<12}  "
                f"MACD: {macd_str}  "
                f"-> {s.recommendation}"
            )
        print()

    total = len(signals)
    n_buy = len(buys)
    n_avoid = len(avoids)
    n_neutral = len(neutral)
    print(
        f"Market Summary: {n_buy} BUY | {n_avoid} AVOID | {n_neutral} NEUTRAL "
        f"({total} symbols scanned)"
    )
    print()
    print(
        "DEGIRO: Execute BUY orders at market open "
        "(09:00 AMS for AEX, 15:30 AMS for US stocks)."
    )
    print("Use limit orders ±0.5% from current price to avoid slippage.")
    print()


def print_json_report(signals: List[Signal], min_score: float) -> None:
    out: Dict[str, Any] = {
        "scannedAt": datetime.now(timezone.utc).isoformat(),
        "total": len(signals),
        "buys": [asdict(s) for s in signals if s.score >= min_score],
        "avoids": [asdict(s) for s in signals if s.score < 0],
        "neutral": [asdict(s) for s in signals if 0 <= s.score < min_score],
    }
    print(json.dumps(out, indent=2))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Market scanner for DEGIRO — technical analysis signals."
    )
    parser.add_argument(
        "--watchlist",
        choices=list(WATCHLISTS.keys()),
        default="all",
        help="Which symbols to scan (default: all)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        metavar="N",
        help="Number of top BUY picks to show (default: 5)",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=1.0,
        metavar="SCORE",
        help="Minimum score to qualify as a BUY signal (default: 1.0)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output machine-readable JSON",
    )
    args = parser.parse_args()

    symbols = WATCHLISTS[args.watchlist]

    if not args.output_json:
        print(f"Scanning {len(symbols)} symbols from watchlist '{args.watchlist}'...")

    signals: List[Signal] = []
    failed: List[str] = []

    for sym in symbols:
        result = analyse_symbol(sym)
        if result is not None:
            signals.append(result)
        else:
            failed.append(sym)

    if not signals:
        print("No data retrieved. Check network connection.", file=sys.stderr)
        return 1

    if failed and not args.output_json:
        print(f"Could not fetch data for: {', '.join(failed)}\n")

    if args.output_json:
        print_json_report(signals, args.min_score)
    else:
        print_text_report(signals, args.top, args.min_score)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
