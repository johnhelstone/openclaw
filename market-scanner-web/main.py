#!/usr/bin/env python3
"""
main.py — DEGIRO Market Scanner Web App
Standalone FastAPI app met mobile-first dashboard.

Start: python main.py
Open:  http://localhost:8000  (of jouw IP:8000 op telefoon)
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    from fastapi import FastAPI, Query
    from fastapi.responses import HTMLResponse, JSONResponse
    import uvicorn
except ImportError:
    raise ImportError("Run: pip install fastapi uvicorn")

from scanner_core import scan_markets, run_backtest

# ---------------------------------------------------------------------------
# App + cache
# ---------------------------------------------------------------------------

app = FastAPI(title="DEGIRO Market Scanner")

CACHE_FILE = Path(__file__).parent / ".last_scan.json"
_cache: dict = {"scan": None, "backtest": None}
_lock = threading.Lock()


def _load_cache() -> None:
    if CACHE_FILE.exists():
        try:
            data = json.loads(CACHE_FILE.read_text())
            _cache["scan"] = data.get("scan")
        except Exception:
            pass


def _save_cache() -> None:
    try:
        CACHE_FILE.write_text(json.dumps({"scan": _cache["scan"]}, default=str))
    except Exception:
        pass


_load_cache()

# ---------------------------------------------------------------------------
# HTML — mobile-first trading dashboard (embedded, zero external deps)
# ---------------------------------------------------------------------------

HTML = """<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<title>DEGIRO Scanner</title>
<style>
  :root {
    --bg: #0d1117;
    --surface: #161b22;
    --surface2: #21262d;
    --border: #30363d;
    --text: #e6edf3;
    --muted: #8b949e;
    --green: #3fb950;
    --green-dim: #1a3a20;
    --green-bright: #56d364;
    --red: #f85149;
    --red-dim: #3a1a1a;
    --orange: #d29922;
    --orange-dim: #3a2d10;
    --blue: #58a6ff;
    --radius: 12px;
    --radius-sm: 8px;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 15px;
    min-height: 100vh;
    padding-bottom: 40px;
  }

  /* Header */
  .header {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 16px 20px 12px;
    position: sticky;
    top: 0;
    z-index: 100;
  }
  .header-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
  }
  .logo { font-size: 20px; font-weight: 700; letter-spacing: -0.5px; }
  .logo span { color: var(--green); }
  .last-scan { font-size: 12px; color: var(--muted); }

  /* Controls */
  .controls {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }
  select, .btn {
    height: 40px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border);
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    outline: none;
    -webkit-tap-highlight-color: transparent;
  }
  select {
    background: var(--surface2);
    color: var(--text);
    padding: 0 12px;
    flex: 1;
    min-width: 100px;
  }
  .btn {
    padding: 0 18px;
    transition: opacity .15s, transform .1s;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .btn:active { transform: scale(0.96); opacity: .8; }
  .btn-primary { background: var(--green); color: #000; border-color: var(--green); }
  .btn-secondary { background: var(--surface2); color: var(--text); }
  .btn-backtest { background: #1f4fd8; color: #fff; border-color: #1f4fd8; }
  .btn:disabled { opacity: .4; cursor: not-allowed; }

  /* Spinner */
  .spinner {
    display: none;
    width: 18px; height: 18px;
    border: 2px solid rgba(0,0,0,0.3);
    border-top-color: #000;
    border-radius: 50%;
    animation: spin .7s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* Main content */
  .content { padding: 16px 16px 0; max-width: 600px; margin: 0 auto; }

  /* Status banner */
  .banner {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 14px 16px;
    margin-bottom: 16px;
    text-align: center;
    color: var(--muted);
    font-size: 14px;
  }
  .banner.loading { color: var(--blue); border-color: var(--blue); }
  .banner.error { color: var(--red); border-color: var(--red); }

  /* Summary bar */
  .summary {
    display: flex;
    gap: 8px;
    margin-bottom: 16px;
  }
  .summary-chip {
    flex: 1;
    text-align: center;
    padding: 10px 4px;
    border-radius: var(--radius-sm);
    font-size: 13px;
    font-weight: 700;
  }
  .chip-buy { background: var(--green-dim); color: var(--green-bright); }
  .chip-avoid { background: var(--red-dim); color: var(--red); }
  .chip-neutral { background: var(--surface2); color: var(--muted); }

  /* Section header */
  .section-title {
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .8px;
    color: var(--muted);
    margin: 20px 0 10px;
  }

  /* Signal card */
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 14px 16px;
    margin-bottom: 10px;
    border-left: 4px solid var(--border);
  }
  .card.buy { border-left-color: var(--green); }
  .card.strong-buy { border-left-color: var(--green-bright); background: #0d1f10; }
  .card.avoid { border-left-color: var(--red); }
  .card.strong-avoid { border-left-color: var(--red); background: #1f0d0d; }
  .card.neutral { border-left-color: var(--border); }

  .card-top {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 8px;
  }
  .card-left { display: flex; flex-direction: column; gap: 2px; }
  .ticker { font-size: 17px; font-weight: 700; }
  .company { font-size: 13px; color: var(--muted); }
  .card-right { text-align: right; }
  .price { font-size: 17px; font-weight: 700; }
  .change { font-size: 13px; margin-top: 2px; }
  .change.up { color: var(--green); }
  .change.down { color: var(--red); }

  .badges {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    margin-bottom: 8px;
  }
  .badge {
    font-size: 11px;
    font-weight: 700;
    padding: 3px 8px;
    border-radius: 20px;
    letter-spacing: .3px;
  }
  .badge-rec {
    padding: 4px 10px;
    font-size: 12px;
  }
  .badge-green { background: var(--green-dim); color: var(--green-bright); }
  .badge-red { background: var(--red-dim); color: var(--red); }
  .badge-orange { background: var(--orange-dim); color: var(--orange); }
  .badge-grey { background: var(--surface2); color: var(--muted); }
  .badge-blue { background: #0d1f3c; color: var(--blue); }

  .score-bar-wrap {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
  }
  .score-label { font-size: 12px; color: var(--muted); width: 50px; }
  .score-bar {
    flex: 1;
    height: 6px;
    background: var(--surface2);
    border-radius: 3px;
    overflow: hidden;
  }
  .score-fill {
    height: 100%;
    border-radius: 3px;
    transition: width .4s ease;
  }
  .score-val { font-size: 13px; font-weight: 700; width: 36px; text-align: right; }

  .reasons { display: flex; flex-direction: column; gap: 3px; margin-top: 6px; }
  .reason {
    font-size: 12px;
    color: var(--muted);
    padding-left: 12px;
    position: relative;
  }
  .reason::before {
    content: "•";
    position: absolute;
    left: 0;
    color: var(--muted);
  }

  /* Backtest results */
  .bt-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-bottom: 16px;
  }
  .bt-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 14px;
    text-align: center;
  }
  .bt-val {
    font-size: 22px;
    font-weight: 700;
    margin-bottom: 4px;
  }
  .bt-label { font-size: 12px; color: var(--muted); }
  .bt-positive { color: var(--green); }
  .bt-negative { color: var(--red); }
  .bt-neutral { color: var(--blue); }

  .symbol-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    margin-top: 8px;
  }
  .symbol-table th {
    text-align: left;
    color: var(--muted);
    font-weight: 600;
    padding: 8px 6px 4px;
    border-bottom: 1px solid var(--border);
    font-size: 11px;
    text-transform: uppercase;
  }
  .symbol-table td {
    padding: 8px 6px;
    border-bottom: 1px solid var(--border);
  }
  .symbol-table tr:last-child td { border-bottom: none; }

  /* Tabs */
  .tabs {
    display: flex;
    gap: 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 0;
    overflow-x: auto;
  }
  .tab {
    padding: 10px 16px;
    font-size: 13px;
    font-weight: 600;
    color: var(--muted);
    cursor: pointer;
    border-bottom: 2px solid transparent;
    white-space: nowrap;
    -webkit-tap-highlight-color: transparent;
    transition: color .15s;
  }
  .tab.active {
    color: var(--text);
    border-bottom-color: var(--blue);
  }

  /* Empty state */
  .empty {
    text-align: center;
    padding: 40px 20px;
    color: var(--muted);
    font-size: 14px;
  }

  /* DEGIRO tip */
  .tip {
    background: #0d1f3c;
    border: 1px solid #1f3a5c;
    border-radius: var(--radius);
    padding: 12px 14px;
    font-size: 13px;
    color: var(--blue);
    margin-top: 16px;
  }
  .tip strong { display: block; margin-bottom: 4px; color: #7db8ff; }
</style>
</head>
<body>

<div class="header">
  <div class="header-top">
    <div class="logo">📈 DEGIRO <span>Scanner</span></div>
    <div class="last-scan" id="lastScan">Nog niet gescand</div>
  </div>
  <div class="controls">
    <select id="watchlist">
      <option value="all">Alle markten</option>
      <option value="aex">AEX Amsterdam</option>
      <option value="us">US Aandelen</option>
      <option value="commodities">Grondstoffen</option>
    </select>
    <button class="btn btn-primary" id="scanBtn" onclick="startScan()">
      <div class="spinner" id="scanSpinner"></div>
      <span id="scanLabel">Scan nu</span>
    </button>
    <button class="btn btn-backtest" id="btBtn" onclick="startBacktest()">
      <div class="spinner" id="btSpinner" style="border-top-color:#fff;border-color:rgba(255,255,255,.3)"></div>
      <span id="btLabel">Backtest</span>
    </button>
  </div>
</div>

<div class="content">

  <!-- Banner -->
  <div id="banner" class="banner" style="display:none"></div>

  <!-- Tabs -->
  <div id="tabs" class="tabs" style="display:none">
    <div class="tab active" onclick="showTab('scan')">Signalen</div>
    <div class="tab" onclick="showTab('backtest')">Backtest</div>
  </div>

  <!-- Scan results -->
  <div id="scanPanel">
    <div class="empty" id="emptyState">
      Druk op <strong>Scan nu</strong> om de markten te analyseren.<br><br>
      Scant AEX, S&P 500 en grondstoffen via Yahoo Finance (gratis).
    </div>
    <div id="scanResults" style="display:none"></div>
  </div>

  <!-- Backtest panel -->
  <div id="btPanel" style="display:none">
    <div id="btResults"></div>
  </div>

</div>

<script>
let scanData = null;
let btData = null;
let currentTab = 'scan';

function showTab(tab) {
  currentTab = tab;
  document.querySelectorAll('.tab').forEach((t, i) => {
    t.classList.toggle('active', (i === 0 && tab === 'scan') || (i === 1 && tab === 'backtest'));
  });
  document.getElementById('scanPanel').style.display = tab === 'scan' ? 'block' : 'none';
  document.getElementById('btPanel').style.display = tab === 'backtest' ? 'block' : 'none';
}

function setBanner(msg, type='loading') {
  const b = document.getElementById('banner');
  b.textContent = msg;
  b.className = 'banner ' + type;
  b.style.display = msg ? 'block' : 'none';
}

function fmtPrice(price, currency) {
  const sym = currency === 'EUR' ? '€' : '$';
  return sym + (price >= 1000 ? price.toLocaleString('nl-NL', {minimumFractionDigits:2,maximumFractionDigits:2}) : price.toFixed(2));
}

function recClass(rec) {
  if (rec === 'STRONG BUY') return 'strong-buy';
  if (rec === 'BUY') return 'buy';
  if (rec === 'AVOID' || rec === 'STRONG AVOID') return 'avoid';
  return 'neutral';
}

function recBadgeClass(rec) {
  if (rec.includes('BUY')) return 'badge-green';
  if (rec.includes('AVOID')) return 'badge-red';
  return 'badge-grey';
}

function scoreColor(score) {
  if (score >= 1.5) return '#3fb950';
  if (score >= 0.5) return '#56d364';
  if (score <= -0.5) return '#f85149';
  return '#8b949e';
}

function renderSignal(s) {
  const changeCls = s.change_pct >= 0 ? 'up' : 'down';
  const changeStr = (s.change_pct >= 0 ? '+' : '') + s.change_pct.toFixed(2) + '%';
  const scoreNorm = Math.min(Math.max((s.score + 3) / 6, 0), 1);
  const scoreWidth = (scoreNorm * 100).toFixed(0);
  const reasons = s.reasons.slice(0, 3).map(r => `<div class="reason">${r}</div>`).join('');
  const macdBadge = s.macd_bullish
    ? '<span class="badge badge-green">MACD ↑</span>'
    : '<span class="badge badge-red">MACD ↓</span>';
  const smaBadge = s.above_sma50
    ? '<span class="badge badge-blue">SMA50 ✓</span>'
    : '<span class="badge badge-grey">SMA50 ✗</span>';
  const rsiBadge = `<span class="badge badge-grey">RSI ${s.rsi.toFixed(0)}</span>`;
  const recBadge = `<span class="badge badge-rec ${recBadgeClass(s.recommendation)}">${s.recommendation}</span>`;

  return `
  <div class="card ${recClass(s.recommendation)}">
    <div class="card-top">
      <div class="card-left">
        <div class="ticker">${s.symbol}</div>
        <div class="company">${s.name}</div>
      </div>
      <div class="card-right">
        <div class="price">${fmtPrice(s.price, s.currency)}</div>
        <div class="change ${changeCls}">${changeStr} vandaag</div>
      </div>
    </div>
    <div class="badges">${recBadge}${macdBadge}${smaBadge}${rsiBadge}</div>
    <div class="score-bar-wrap">
      <div class="score-label">Score</div>
      <div class="score-bar">
        <div class="score-fill" style="width:${scoreWidth}%;background:${scoreColor(s.score)}"></div>
      </div>
      <div class="score-val" style="color:${scoreColor(s.score)}">${s.score > 0 ? '+' : ''}${s.score.toFixed(1)}</div>
    </div>
    <div class="reasons">${reasons}</div>
  </div>`;
}

function renderScan(data) {
  scanData = data;
  const ts = new Date(data.scanned_at);
  document.getElementById('lastScan').textContent = 'Scan: ' + ts.toLocaleTimeString('nl-NL', {hour:'2-digit',minute:'2-digit'});

  let html = '';

  // Summary chips
  html += `<div class="summary">
    <div class="summary-chip chip-buy">🟢 ${data.buys.length} Koop</div>
    <div class="summary-chip chip-neutral">⚪ ${data.neutral.length} Neutraal</div>
    <div class="summary-chip chip-avoid">🔴 ${data.avoids.length} Vermijd</div>
  </div>`;

  if (data.buys.length > 0) {
    html += '<div class="section-title">Koop signalen</div>';
    data.buys.forEach(s => { html += renderSignal(s); });
  }

  if (data.avoids.length > 0) {
    html += '<div class="section-title">Vermijd / Verkoop</div>';
    data.avoids.forEach(s => { html += renderSignal(s); });
  }

  if (data.buys.length === 0 && data.avoids.length === 0) {
    html += '<div class="empty">Geen sterke signalen gevonden. Probeer een lagere drempelwaarde of een andere watchlist.</div>';
  }

  // DEGIRO tip
  html += `<div class="tip">
    <strong>💡 DEGIRO tip</strong>
    Voer koop-orders uit bij marktopening (09:00 AEX, 15:30 US). Gebruik limiet-orders ±0.5% van de huidige prijs. Stel stop-loss in op −5%.
  </div>`;

  document.getElementById('emptyState').style.display = 'none';
  const el = document.getElementById('scanResults');
  el.innerHTML = html;
  el.style.display = 'block';

  document.getElementById('tabs').style.display = 'flex';
  showTab('scan');
}

function renderBacktest(data) {
  btData = data;
  if (data.error) {
    document.getElementById('btResults').innerHTML = `<div class="empty">${data.error}</div>`;
    return;
  }

  const totalRet = data.total_return_pct;
  const retClass = totalRet >= 0 ? 'bt-positive' : 'bt-negative';
  const ddClass = 'bt-negative';

  let html = `
  <div class="section-title" style="margin-top:16px">Resultaten — ${data.period} periode</div>
  <div class="bt-grid">
    <div class="bt-card">
      <div class="bt-val ${retClass}">${totalRet >= 0 ? '+' : ''}${totalRet}%</div>
      <div class="bt-label">Totaal rendement</div>
    </div>
    <div class="bt-card">
      <div class="bt-val bt-neutral">${data.win_rate}%</div>
      <div class="bt-label">Win rate</div>
    </div>
    <div class="bt-card">
      <div class="bt-val ${ddClass}">${data.max_drawdown_pct}%</div>
      <div class="bt-label">Max drawdown</div>
    </div>
    <div class="bt-card">
      <div class="bt-val bt-neutral">${data.total_trades}</div>
      <div class="bt-label">Trades</div>
    </div>
  </div>
  <div class="bt-card" style="margin-bottom:10px">
    <div style="display:flex;justify-content:space-between;font-size:13px">
      <span style="color:var(--muted)">Startkapitaal</span>
      <span>€${data.capital.toLocaleString('nl-NL')}</span>
    </div>
    <div style="display:flex;justify-content:space-between;font-size:15px;font-weight:700;margin-top:8px">
      <span style="color:var(--muted)">Eindkapitaal</span>
      <span class="${retClass}">€${data.final_capital.toLocaleString('nl-NL',{minimumFractionDigits:2,maximumFractionDigits:2})}</span>
    </div>
  </div>
  <div class="section-title">Per aandeel</div>
  <div class="card">
  <table class="symbol-table">
    <tr><th>Aandeel</th><th>Trades</th><th>Win%</th><th>Rendement</th></tr>`;

  data.per_symbol.forEach(s => {
    const rc = s.return_pct >= 0 ? 'color:var(--green)' : 'color:var(--red)';
    html += `<tr>
      <td><strong>${s.symbol}</strong><br><span style="color:var(--muted);font-size:11px">${s.name}</span></td>
      <td>${s.trades}</td>
      <td>${s.win_rate}%</td>
      <td style="${rc};font-weight:700">${s.return_pct >= 0 ? '+' : ''}${s.return_pct}%</td>
    </tr>`;
  });

  html += `</table></div>
  <div class="tip" style="margin-top:12px">
    <strong>⚠️ Disclaimer</strong>
    Backtest resultaten zijn gebaseerd op historische data. Verleden prestaties zijn geen garantie voor de toekomst. Dit is geen financieel advies.
  </div>`;

  document.getElementById('btResults').innerHTML = html;
  document.getElementById('tabs').style.display = 'flex';
  showTab('backtest');
}

async function startScan() {
  const btn = document.getElementById('scanBtn');
  const spinner = document.getElementById('scanSpinner');
  const label = document.getElementById('scanLabel');
  const wl = document.getElementById('watchlist').value;

  btn.disabled = true;
  spinner.style.display = 'block';
  label.textContent = 'Bezig...';
  setBanner('Marktdata ophalen via Yahoo Finance... (dit duurt 15–30 seconden)');

  try {
    const res = await fetch(`/api/scan?watchlist=${wl}`);
    if (!res.ok) throw new Error('Server fout: ' + res.status);
    const data = await res.json();
    setBanner('');
    renderScan(data);
  } catch (e) {
    setBanner('Fout: ' + e.message + ' — Controleer je internetverbinding.', 'error');
  } finally {
    btn.disabled = false;
    spinner.style.display = 'none';
    label.textContent = 'Scan nu';
  }
}

async function startBacktest() {
  const btn = document.getElementById('btBtn');
  const spinner = document.getElementById('btSpinner');
  const label = document.getElementById('btLabel');
  const wl = document.getElementById('watchlist').value;

  btn.disabled = true;
  spinner.style.display = 'block';
  label.textContent = 'Bezig...';
  setBanner('Backtest uitvoeren over 2 jaar historische data... (dit duurt 1–3 minuten)');

  try {
    const res = await fetch(`/api/backtest?watchlist=${wl}&period=2y&capital=10000`);
    if (!res.ok) throw new Error('Server fout: ' + res.status);
    const data = await res.json();
    setBanner('');
    renderBacktest(data);
  } catch (e) {
    setBanner('Fout: ' + e.message, 'error');
  } finally {
    btn.disabled = false;
    spinner.style.display = 'none';
    label.textContent = 'Backtest';
  }
}

// Load cached scan on startup
window.addEventListener('load', async () => {
  try {
    const res = await fetch('/api/last');
    const data = await res.json();
    if (data && data.signals) renderScan(data);
  } catch (_) {}
});
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return HTML


@app.get("/api/scan")
async def api_scan(
    watchlist: str = Query("all"),
    min_score: float = Query(0.5),
):
    import asyncio
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: scan_markets(watchlist, min_score))
    with _lock:
        _cache["scan"] = result
    _save_cache()
    return JSONResponse(result)


@app.get("/api/backtest")
async def api_backtest(
    watchlist: str = Query("all"),
    period: str = Query("2y"),
    capital: float = Query(10000),
    stop_loss: float = Query(0.05),
    take_profit: float = Query(0.15),
):
    import asyncio
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: run_backtest(watchlist, period, capital, stop_loss, take_profit),
    )
    return JSONResponse(result)


@app.get("/api/last")
async def api_last():
    with _lock:
        data = _cache.get("scan")
    if data is None:
        return JSONResponse({"error": "Nog geen scan"}, status_code=404)
    return JSONResponse(data)


@app.get("/api/health")
async def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    print(f"\n{'='*50}")
    print(f"  DEGIRO Market Scanner")
    print(f"  Open op deze computer: http://localhost:{port}")
    print(f"  Open op telefoon:      http://<jouw-IP>:{port}")
    print(f"{'='*50}\n")
    uvicorn.run(app, host=host, port=port, log_level="warning")
