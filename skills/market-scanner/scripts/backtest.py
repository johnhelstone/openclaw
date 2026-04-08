#!/usr/bin/env python3
"""
Backtesting Engine for DEGIRO Market Scanner — OpenClaw Skill
=============================================================
Walk-forward backtest of the RSI + MACD + MA + Bollinger strategy.
No lookahead bias: signals are computed at day close, trades enter next open.

Usage:
    python backtest.py [--period 2y] [--capital 10000]
                       [--stop-loss 0.05] [--take-profit 0.15]
                       [--watchlist all|aex|us|commodities]
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Tuple

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
# Watchlists (same as scanner.py)
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
# Indicator functions (replicated from scanner.py, no shared import needed)
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
    close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> Tuple[pd.Series, pd.Series]:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line


def compute_sma(close: pd.Series, period: int) -> pd.Series:
    return close.rolling(period).mean()


def compute_bollinger(
    close: pd.Series, period: int = 20, num_std: float = 2.0
) -> Tuple[pd.Series, pd.Series]:
    mid = close.rolling(period).mean()
    std = close.rolling(period).std()
    return mid + num_std * std, mid - num_std * std


# ---------------------------------------------------------------------------
# Signal computation (returns score series for entire history)
# ---------------------------------------------------------------------------

def compute_signal_series(close: pd.Series) -> pd.Series:
    """Return a daily score series aligned to close index."""
    scores = pd.Series(0.0, index=close.index)

    rsi = compute_rsi(close)
    macd_line, signal_line = compute_macd(close)
    sma50 = compute_sma(close, 50)
    sma200 = compute_sma(close, 200)
    bb_upper, bb_lower = compute_bollinger(close)

    for i in range(1, len(close)):
        score = 0.0
        r = float(rsi.iloc[i]) if not np.isnan(rsi.iloc[i]) else 50.0
        m = float(macd_line.iloc[i]) if not np.isnan(macd_line.iloc[i]) else 0.0
        s = float(signal_line.iloc[i]) if not np.isnan(signal_line.iloc[i]) else 0.0
        m_prev = float(macd_line.iloc[i - 1]) if not np.isnan(macd_line.iloc[i - 1]) else 0.0
        s_prev = float(signal_line.iloc[i - 1]) if not np.isnan(signal_line.iloc[i - 1]) else 0.0
        p = float(close.iloc[i])

        # RSI
        if 30 <= r <= 50:
            score += 1.0
        elif r < 30:
            score += 0.5
        elif r > 70:
            score -= 1.0

        # MACD crossover
        cross_up = m_prev <= s_prev and m > s
        cross_down = m_prev >= s_prev and m < s
        if cross_up:
            score += 1.0
        elif m > s:
            score += 0.5
        if cross_down:
            score -= 1.0
        elif m < s:
            score -= 0.5

        # Trend
        if not np.isnan(sma50.iloc[i]) and p > float(sma50.iloc[i]):
            score += 0.5
        if not np.isnan(sma200.iloc[i]) and p > float(sma200.iloc[i]):
            score += 0.5

        # Bollinger
        if not np.isnan(bb_upper.iloc[i]):
            u = float(bb_upper.iloc[i])
            lo = float(bb_lower.iloc[i])
            band_range = u - lo if u != lo else 1.0
            pct = (p - lo) / band_range
            if pct <= 0.02:
                score += 0.5
            elif pct >= 0.98:
                score -= 0.5

        scores.iloc[i] = round(score, 2)

    return scores


# ---------------------------------------------------------------------------
# Trade log
# ---------------------------------------------------------------------------

@dataclass
class Trade:
    symbol: str
    entry_date: date
    entry_price: float
    exit_date: Optional[date]
    exit_price: Optional[float]
    exit_reason: str  # "signal", "stop_loss", "take_profit", "end"
    pnl_pct: Optional[float]
    pnl_eur: Optional[float]


# ---------------------------------------------------------------------------
# Backtest engine
# ---------------------------------------------------------------------------

def fetch_data(symbols: List[str], period: str) -> Dict[str, pd.DataFrame]:
    """Download OHLCV for all symbols."""
    print(f"Downloading {len(symbols)} symbols ({period} history)...")
    data: Dict[str, pd.DataFrame] = {}
    for sym in symbols:
        try:
            df = yf.Ticker(sym).history(period=period, interval="1d", auto_adjust=True)
            if df is not None and len(df) >= 60:
                data[sym] = df
        except Exception:
            pass
    print(f"Loaded {len(data)}/{len(symbols)} symbols.\n")
    return data


def run_backtest(
    symbols: List[str],
    period: str,
    starting_capital: float,
    stop_loss: float,
    take_profit: float,
    min_score: float = 1.0,
) -> None:
    raw = fetch_data(symbols, period)
    if not raw:
        print("No data available. Check network connection.", file=sys.stderr)
        return

    # Pre-compute signal series for each symbol
    print("Computing signals for each symbol...")
    signal_series: Dict[str, pd.Series] = {}
    close_series: Dict[str, pd.Series] = {}
    open_series: Dict[str, pd.Series] = {}

    for sym, df in raw.items():
        close = df["Close"].dropna()
        opens = df["Open"].dropna()
        if len(close) < 60:
            continue
        signal_series[sym] = compute_signal_series(close)
        close_series[sym] = close
        open_series[sym] = opens

    if not signal_series:
        print("Insufficient data for backtest.", file=sys.stderr)
        return

    # Build unified date index (union of all dates)
    all_dates = sorted(
        set().union(*[set(s.index) for s in signal_series.values()])
    )

    # Walk-forward simulation
    capital = starting_capital
    equity_curve: List[Tuple[date, float]] = [(all_dates[0].date(), capital)]
    open_positions: Dict[str, Tuple[float, date]] = {}  # sym -> (entry_price, entry_date)
    all_trades: List[Trade] = []

    for i, dt in enumerate(all_dates[:-1]):
        next_dt = all_dates[i + 1]

        # 1. Check exits for open positions
        to_close: List[str] = []
        for sym, (entry_price, entry_date) in open_positions.items():
            if sym not in close_series:
                continue
            close_s = close_series[sym]
            if dt not in close_s.index:
                continue
            current_price = float(close_s.loc[dt])
            pnl_pct = (current_price - entry_price) / entry_price

            exit_reason = None
            exit_price = None

            if pnl_pct <= -stop_loss:
                exit_reason = "stop_loss"
                # Use open of next day as exit (realistic)
                if sym in open_series and next_dt in open_series[sym].index:
                    exit_price = float(open_series[sym].loc[next_dt])
                else:
                    exit_price = current_price
            elif pnl_pct >= take_profit:
                exit_reason = "take_profit"
                if sym in open_series and next_dt in open_series[sym].index:
                    exit_price = float(open_series[sym].loc[next_dt])
                else:
                    exit_price = current_price
            else:
                # Check signal reversal
                sig_s = signal_series[sym]
                if dt in sig_s.index and float(sig_s.loc[dt]) < 0:
                    exit_reason = "signal"
                    if sym in open_series and next_dt in open_series[sym].index:
                        exit_price = float(open_series[sym].loc[next_dt])
                    else:
                        exit_price = current_price

            if exit_reason and exit_price:
                realized_pnl_pct = (exit_price - entry_price) / entry_price
                position_size = capital / max(len(open_positions), 1)
                realized_pnl_eur = position_size * realized_pnl_pct
                capital += realized_pnl_eur
                all_trades.append(
                    Trade(
                        symbol=sym,
                        entry_date=entry_date,
                        entry_price=entry_price,
                        exit_date=next_dt.date(),
                        exit_price=exit_price,
                        exit_reason=exit_reason,
                        pnl_pct=round(realized_pnl_pct * 100, 2),
                        pnl_eur=round(realized_pnl_eur, 2),
                    )
                )
                to_close.append(sym)

        for sym in to_close:
            del open_positions[sym]

        # 2. Check for new entry signals (signal computed at close of dt)
        for sym, sig_s in signal_series.items():
            if sym in open_positions:
                continue
            if dt not in sig_s.index:
                continue
            score = float(sig_s.loc[dt])
            if score >= min_score:
                # Enter at next-day open
                if sym in open_series and next_dt in open_series[sym].index:
                    entry_price = float(open_series[sym].loc[next_dt])
                    open_positions[sym] = (entry_price, next_dt.date())

        equity_curve.append((dt.date(), round(capital, 2)))

    # Close remaining positions at last date
    last_dt = all_dates[-1]
    for sym, (entry_price, entry_date) in open_positions.items():
        if sym not in close_series or last_dt not in close_series[sym].index:
            continue
        exit_price = float(close_series[sym].loc[last_dt])
        realized_pnl_pct = (exit_price - entry_price) / entry_price
        position_size = starting_capital / max(len(open_positions), 1)
        realized_pnl_eur = position_size * realized_pnl_pct
        capital += realized_pnl_eur
        all_trades.append(
            Trade(
                symbol=sym,
                entry_date=entry_date,
                entry_price=entry_price,
                exit_date=last_dt.date(),
                exit_price=exit_price,
                exit_reason="end",
                pnl_pct=round(realized_pnl_pct * 100, 2),
                pnl_eur=round(realized_pnl_eur, 2),
            )
        )

    # ---------------------------------------------------------------------------
    # Performance metrics
    # ---------------------------------------------------------------------------

    total_return_pct = (capital - starting_capital) / starting_capital * 100
    days_total = (all_dates[-1].date() - all_dates[0].date()).days
    years = days_total / 365.25
    annual_return_pct = ((capital / starting_capital) ** (1 / max(years, 0.1)) - 1) * 100

    # Sharpe ratio (daily returns)
    equity_values = [v for _, v in equity_curve]
    if len(equity_values) > 2:
        eq_series = pd.Series(equity_values)
        daily_returns = eq_series.pct_change().dropna()
        rf_daily = 0.03 / 252  # 3% annual risk-free rate
        excess = daily_returns - rf_daily
        sharpe = (excess.mean() / excess.std() * np.sqrt(252)) if excess.std() > 0 else 0.0
    else:
        sharpe = 0.0

    # Max drawdown
    eq_series = pd.Series([v for _, v in equity_curve])
    rolling_max = eq_series.cummax()
    drawdowns = (eq_series - rolling_max) / rolling_max
    max_dd = float(drawdowns.min()) * 100

    # Trade stats
    completed = [t for t in all_trades if t.pnl_pct is not None]
    wins = [t for t in completed if (t.pnl_pct or 0) > 0]
    losses = [t for t in completed if (t.pnl_pct or 0) <= 0]
    win_rate = len(wins) / len(completed) * 100 if completed else 0
    avg_win = sum(t.pnl_pct or 0 for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t.pnl_pct or 0 for t in losses) / len(losses) if losses else 0
    best = max(completed, key=lambda t: t.pnl_pct or 0, default=None)
    worst = min(completed, key=lambda t: t.pnl_pct or 0, default=None)

    # ---------------------------------------------------------------------------
    # Print report
    # ---------------------------------------------------------------------------

    print("=" * 65)
    print("BACKTEST RESULTS")
    print("=" * 65)
    print(f"Period          : {all_dates[0].date()} — {all_dates[-1].date()} ({years:.1f} years)")
    print(f"Starting capital: €{starting_capital:,.0f}")
    print(f"Final capital   : €{capital:,.2f}")
    print()
    print(f"Total return    : {total_return_pct:+.1f}%")
    print(f"Annual return   : {annual_return_pct:+.1f}%")
    print(f"Sharpe ratio    : {sharpe:.2f}")
    print(f"Max drawdown    : {max_dd:.1f}%")
    print()
    print(f"Trades total    : {len(completed)}")
    print(f"Win rate        : {win_rate:.1f}%  ({len(wins)} wins / {len(losses)} losses)")
    print(f"Avg win         : {avg_win:+.1f}%")
    print(f"Avg loss        : {avg_loss:+.1f}%")

    if best:
        print(f"Best trade      : {best.symbol} {best.pnl_pct:+.1f}%  "
              f"({best.entry_date} → {best.exit_date})")
    if worst:
        print(f"Worst trade     : {worst.symbol} {worst.pnl_pct:+.1f}%  "
              f"({worst.entry_date} → {worst.exit_date})")

    print()
    print("Exit breakdown:")
    reasons = {}
    for t in completed:
        reasons[t.exit_reason] = reasons.get(t.exit_reason, 0) + 1
    for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
        print(f"  {reason:<15}: {count}")

    print()
    print("Last 10 trades:")
    print(f"{'Symbol':<12} {'Entry':>12} {'Exit':>12} {'PnL%':>8} {'Reason'}")
    print("-" * 60)
    for t in completed[-10:]:
        pnl_str = f"{t.pnl_pct:+.1f}%" if t.pnl_pct is not None else "—"
        print(
            f"{t.symbol:<12} "
            f"{str(t.entry_date):>12} "
            f"{str(t.exit_date):>12} "
            f"{pnl_str:>8}   "
            f"{t.exit_reason}"
        )
    print()
    print("=" * 65)

    # Risk note
    if annual_return_pct < 0:
        print("NOTE: Strategy underperformed in this period. Consider adjusting")
        print("      parameters or verifying data quality before live trading.")
    elif sharpe < 0.5:
        print("NOTE: Low Sharpe ratio. Returns may not justify the volatility.")
    else:
        print("Strategy shows positive edge. Always paper-trade before going live.")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Walk-forward backtest of the DEGIRO market scanner strategy."
    )
    parser.add_argument(
        "--watchlist",
        choices=list(WATCHLISTS.keys()),
        default="all",
        help="Symbols to test (default: all)",
    )
    parser.add_argument(
        "--period",
        choices=["1y", "2y"],
        default="2y",
        help="Historical data period (default: 2y)",
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=10000.0,
        metavar="EUR",
        help="Starting capital in EUR (default: 10000)",
    )
    parser.add_argument(
        "--stop-loss",
        type=float,
        default=0.05,
        metavar="FRAC",
        help="Stop-loss as fraction, e.g. 0.05 = 5%% (default: 0.05)",
    )
    parser.add_argument(
        "--take-profit",
        type=float,
        default=0.15,
        metavar="FRAC",
        help="Take-profit as fraction, e.g. 0.15 = 15%% (default: 0.15)",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=1.0,
        metavar="SCORE",
        help="Minimum score for entry signal (default: 1.0)",
    )
    args = parser.parse_args()

    run_backtest(
        symbols=WATCHLISTS[args.watchlist],
        period=args.period,
        starting_capital=args.capital,
        stop_loss=args.stop_loss,
        take_profit=args.take_profit,
        min_score=args.min_score,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
