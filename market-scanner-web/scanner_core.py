#!/usr/bin/env python3
"""
scanner_core.py — Market scanner engine (importable module)
All indicator logic + signal scoring, returns Python dicts (no printing).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

try:
    import numpy as np
    import pandas as pd
    import yfinance as yf
except ImportError:
    raise ImportError("Run: pip install yfinance pandas numpy")

# ---------------------------------------------------------------------------
# Watchlists
# ---------------------------------------------------------------------------

WATCHLIST_AEX = [
    "ASML.AS", "HEIA.AS", "PHIA.AS", "INGA.AS", "ABN.AS",
    "SHEL.AS", "UNA.AS", "ADYEN.AS", "NN.AS", "AKZA.AS",
]
WATCHLIST_US = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN",
    "META", "JPM", "BRK-B", "JNJ", "XOM",
]
WATCHLIST_COMMODITIES = ["GC=F", "CL=F", "SI=F", "HG=F", "NG=F"]

WATCHLISTS: Dict[str, List[str]] = {
    "aex": WATCHLIST_AEX,
    "us": WATCHLIST_US,
    "commodities": WATCHLIST_COMMODITIES,
    "all": WATCHLIST_AEX + WATCHLIST_US + WATCHLIST_COMMODITIES,
}

# ---------------------------------------------------------------------------
# Indicators
# ---------------------------------------------------------------------------

def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    return 100.0 - (100.0 / (1.0 + rs))


def _macd(close: pd.Series, fast=12, slow=26, signal=9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line


def _sma(close: pd.Series, period: int) -> pd.Series:
    return close.rolling(period).mean()


def _bollinger(close: pd.Series, period=20, num_std=2.0):
    mid = close.rolling(period).mean()
    std = close.rolling(period).std()
    return mid + num_std * std, mid - num_std * std


# ---------------------------------------------------------------------------
# Signal dataclass
# ---------------------------------------------------------------------------

@dataclass
class Signal:
    symbol: str
    name: str
    price: float
    currency: str
    score: float
    rsi: float
    macd_bullish: bool
    above_sma50: bool
    above_sma200: bool
    bb_position: str
    recommendation: str
    reasons: List[str]
    change_pct: float  # 1-day price change %
    group: str  # aex / us / commodities


NAMES = {
    "ASML.AS": "ASML", "HEIA.AS": "Heineken", "PHIA.AS": "Philips",
    "INGA.AS": "ING", "ABN.AS": "ABN AMRO", "SHEL.AS": "Shell",
    "UNA.AS": "Unilever", "ADYEN.AS": "Adyen", "NN.AS": "NN Group",
    "AKZA.AS": "Akzo Nobel", "AAPL": "Apple", "MSFT": "Microsoft",
    "NVDA": "Nvidia", "GOOGL": "Alphabet", "AMZN": "Amazon",
    "META": "Meta", "JPM": "JPMorgan", "BRK-B": "Berkshire",
    "JNJ": "J&J", "XOM": "ExxonMobil", "GC=F": "Gold",
    "CL=F": "Crude Oil", "SI=F": "Silver", "HG=F": "Copper", "NG=F": "Nat.Gas",
}


def _group(symbol: str) -> str:
    if symbol in WATCHLIST_AEX:
        return "aex"
    if symbol in WATCHLIST_US:
        return "us"
    return "commodities"


def _label(score: float) -> str:
    if score >= 2.0:
        return "STRONG BUY"
    if score >= 1.0:
        return "BUY"
    if score <= -1.5:
        return "STRONG AVOID"
    if score <= -0.5:
        return "AVOID"
    return "NEUTRAL"


def analyse_symbol(symbol: str) -> Optional[Signal]:
    try:
        df = yf.Ticker(symbol).history(period="1y", interval="1d", auto_adjust=True)
        if df is None or len(df) < 60:
            return None
    except Exception:
        return None

    close = df["Close"].dropna()
    if len(close) < 60:
        return None

    price = float(close.iloc[-1])
    prev_price = float(close.iloc[-2]) if len(close) > 1 else price
    change_pct = (price - prev_price) / prev_price * 100
    currency = "EUR" if symbol.endswith(".AS") else "USD"

    rsi_s = _rsi(close)
    rsi = float(rsi_s.iloc[-1]) if not rsi_s.isna().iloc[-1] else 50.0

    macd_line, signal_line = _macd(close)
    m = float(macd_line.iloc[-1]) if not macd_line.isna().iloc[-1] else 0.0
    s = float(signal_line.iloc[-1]) if not signal_line.isna().iloc[-1] else 0.0
    macd_bullish = m > s

    m_prev = float(macd_line.iloc[-2]) if len(macd_line) >= 2 and not macd_line.isna().iloc[-2] else m
    s_prev = float(signal_line.iloc[-2]) if len(signal_line) >= 2 and not signal_line.isna().iloc[-2] else s
    fresh_cross_up = m_prev <= s_prev and m > s
    fresh_cross_down = m_prev >= s_prev and m < s

    sma50 = _sma(close, 50)
    sma200 = _sma(close, 200)
    above_sma50 = not sma50.isna().iloc[-1] and price > float(sma50.iloc[-1])
    above_sma200 = not sma200.isna().iloc[-1] and price > float(sma200.iloc[-1])

    bb_upper, bb_lower = _bollinger(close)
    if bb_upper.isna().iloc[-1]:
        bb_pos = "middle"
    else:
        u, lo = float(bb_upper.iloc[-1]), float(bb_lower.iloc[-1])
        band_range = u - lo if u != lo else 1.0
        pct = (price - lo) / band_range
        bb_pos = "lower" if pct <= 0.02 else "upper" if pct >= 0.98 else "middle"

    score = 0.0
    reasons: List[str] = []

    if 30 <= rsi <= 50:
        score += 1.0; reasons.append(f"RSI {rsi:.0f} — herstel van oververkoop")
    elif rsi < 30:
        score += 0.5; reasons.append(f"RSI {rsi:.0f} — sterk oververkocht")
    elif rsi > 70:
        score -= 1.0; reasons.append(f"RSI {rsi:.0f} — overkocht")

    if fresh_cross_up:
        score += 1.0; reasons.append("MACD bullish crossover (vers signaal)")
    elif macd_bullish:
        score += 0.5; reasons.append("MACD bullish")
    elif fresh_cross_down:
        score -= 1.0; reasons.append("MACD bearish crossover (vers signaal)")
    else:
        score -= 0.5; reasons.append("MACD bearish")

    if above_sma50:
        score += 0.5; reasons.append("Prijs boven SMA50 (opwaartse trend)")
    else:
        reasons.append("Prijs onder SMA50")

    if above_sma200:
        score += 0.5; reasons.append("Prijs boven SMA200 (lange termijn bull)")
    else:
        reasons.append("Prijs onder SMA200")

    if bb_pos == "lower":
        score += 0.5; reasons.append("Prijs bij onderkant Bollinger Band")
    elif bb_pos == "upper":
        score -= 0.5; reasons.append("Prijs bij bovenkant Bollinger Band")

    return Signal(
        symbol=symbol,
        name=NAMES.get(symbol, symbol),
        price=price,
        currency=currency,
        score=round(score, 2),
        rsi=round(rsi, 1),
        macd_bullish=macd_bullish,
        above_sma50=above_sma50,
        above_sma200=above_sma200,
        bb_position=bb_pos,
        recommendation=_label(score),
        reasons=reasons,
        change_pct=round(change_pct, 2),
        group=_group(symbol),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scan_markets(watchlist: str = "all", min_score: float = 0.5) -> dict:
    symbols = WATCHLISTS.get(watchlist, WATCHLISTS["all"])
    signals = []
    failed = []
    for sym in symbols:
        result = analyse_symbol(sym)
        if result:
            signals.append(asdict(result))
        else:
            failed.append(sym)

    signals.sort(key=lambda s: s["score"], reverse=True)
    return {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "watchlist": watchlist,
        "total": len(signals),
        "failed": failed,
        "signals": signals,
        "buys": [s for s in signals if s["score"] >= min_score],
        "avoids": [s for s in signals if s["score"] < 0],
        "neutral": [s for s in signals if 0 <= s["score"] < min_score],
    }


def run_backtest(watchlist: str = "all", period: str = "2y",
                 capital: float = 10000, stop_loss: float = 0.05,
                 take_profit: float = 0.15) -> dict:
    """Simplified backtest — returns metrics per symbol."""
    symbols = WATCHLISTS.get(watchlist, WATCHLISTS["all"])
    results = []
    equity = capital
    all_trades = []

    for sym in symbols:
        try:
            df = yf.Ticker(sym).history(period=period, interval="1d", auto_adjust=True)
            if df is None or len(df) < 60:
                continue
        except Exception:
            continue

        close = df["Close"].dropna()
        opens = df["Open"].dropna()
        if len(close) < 60:
            continue

        # Compute signals for full history
        rsi_s = _rsi(close)
        macd_line, signal_line = _macd(close)
        sma50 = _sma(close, 50)
        sma200 = _sma(close, 200)
        bb_upper, bb_lower = _bollinger(close)

        trades = []
        in_trade = False
        entry_price = 0.0

        for i in range(1, len(close) - 1):
            r = float(rsi_s.iloc[i]) if not np.isnan(rsi_s.iloc[i]) else 50.0
            m = float(macd_line.iloc[i]) if not np.isnan(macd_line.iloc[i]) else 0.0
            sg = float(signal_line.iloc[i]) if not np.isnan(signal_line.iloc[i]) else 0.0
            m_prev = float(macd_line.iloc[i-1]) if not np.isnan(macd_line.iloc[i-1]) else m
            s_prev = float(signal_line.iloc[i-1]) if not np.isnan(signal_line.iloc[i-1]) else sg
            p = float(close.iloc[i])

            score = 0.0
            if 30 <= r <= 50: score += 1.0
            elif r < 30: score += 0.5
            elif r > 70: score -= 1.0
            if m_prev <= s_prev and m > sg: score += 1.0
            elif m > sg: score += 0.5
            elif m_prev >= s_prev and m < sg: score -= 1.0
            else: score -= 0.5
            if not np.isnan(sma50.iloc[i]) and p > float(sma50.iloc[i]): score += 0.5
            if not np.isnan(sma200.iloc[i]) and p > float(sma200.iloc[i]): score += 0.5
            if not np.isnan(bb_upper.iloc[i]):
                u, lo = float(bb_upper.iloc[i]), float(bb_lower.iloc[i])
                rng = u - lo if u != lo else 1.0
                pct = (p - lo) / rng
                if pct <= 0.02: score += 0.5
                elif pct >= 0.98: score -= 0.5

            if not in_trade and score >= 1.0 and i + 1 < len(opens):
                entry_price = float(opens.iloc[i + 1])
                in_trade = True
            elif in_trade:
                pnl = (p - entry_price) / entry_price
                if pnl <= -stop_loss or pnl >= take_profit or score < 0:
                    trades.append(pnl)
                    all_trades.append(pnl)
                    in_trade = False

        if not trades:
            continue

        wins = [t for t in trades if t > 0]
        losses = [t for t in trades if t <= 0]
        win_rate = len(wins) / len(trades) * 100

        # Simple equity calc for this symbol
        sym_capital = capital / len(symbols)
        for t in trades:
            sym_capital *= (1 + t)

        results.append({
            "symbol": sym,
            "name": NAMES.get(sym, sym),
            "trades": len(trades),
            "win_rate": round(win_rate, 1),
            "avg_win": round(sum(wins) / len(wins) * 100, 2) if wins else 0,
            "avg_loss": round(sum(losses) / len(losses) * 100, 2) if losses else 0,
            "return_pct": round((sym_capital / (capital / len(symbols)) - 1) * 100, 1),
        })

    # Aggregate
    if not all_trades:
        return {"error": "Geen trades gevonden"}

    wins_all = [t for t in all_trades if t > 0]
    losses_all = [t for t in all_trades if t <= 0]

    eq_curve = [capital]
    pos_size = capital / max(len(symbols), 1)
    for t in all_trades:
        eq_curve.append(eq_curve[-1] + pos_size * t)

    eq_s = pd.Series(eq_curve)
    dd = ((eq_s - eq_s.cummax()) / eq_s.cummax()).min() * 100

    return {
        "period": period,
        "watchlist": watchlist,
        "capital": capital,
        "final_capital": round(eq_curve[-1], 2),
        "total_return_pct": round((eq_curve[-1] / capital - 1) * 100, 1),
        "total_trades": len(all_trades),
        "win_rate": round(len(wins_all) / len(all_trades) * 100, 1),
        "avg_win_pct": round(sum(wins_all) / len(wins_all) * 100, 2) if wins_all else 0,
        "avg_loss_pct": round(sum(losses_all) / len(losses_all) * 100, 2) if losses_all else 0,
        "max_drawdown_pct": round(float(dd), 1),
        "stop_loss_pct": round(stop_loss * 100, 1),
        "take_profit_pct": round(take_profit * 100, 1),
        "per_symbol": sorted(results, key=lambda r: r["return_pct"], reverse=True),
    }
