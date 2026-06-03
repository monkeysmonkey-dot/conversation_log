import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]
RAW_DIR = BASE / "data" / "fundamentals_raw"
SNAPSHOT_PATH = BASE / "features" / "fundamental_snapshots.json"
LATEST_CANDIDATES = BASE / "features" / "latest_candidates.json"

RAW_DIR.mkdir(parents=True, exist_ok=True)

KNOWN_KEYS = [
    "Index", "P/E", "EPS (ttm)", "Insider Own", "Shs Outstand", "Perf Week",
    "Market Cap", "Forward P/E", "EPS next Y", "Insider Trans", "Shs Float", "Perf Month",
    "Enterprise Value", "PEG", "EPS next Q", "Inst Own", "Short Float", "Perf Quarter",
    "Income", "P/S", "EPS this Y", "Inst Trans", "Short Ratio", "Perf Half Y",
    "Sales", "P/B", "ROA", "Short Interest", "Perf YTD",
    "Book/sh", "P/C", "EPS next 5Y", "ROE", "52W High", "Perf Year",
    "Cash/sh", "P/FCF", "EPS past 3/5Y", "ROIC", "52W Low", "Perf 3Y",
    "Dividend Est.", "EV/EBITDA", "Sales past 3/5Y", "Gross Margin", "Volatility", "Perf 5Y",
    "Dividend TTM", "EV/Sales", "EPS Y/Y TTM", "Oper. Margin", "ATR (14)", "Perf 10Y",
    "Dividend Ex-Date", "Quick Ratio", "Sales Y/Y TTM", "Profit Margin", "RSI (14)", "Recom",
    "Dividend Gr. 3/5Y", "Current Ratio", "EPS Q/Q", "SMA20", "Beta", "Target Price",
    "Payout", "Debt/Eq", "Sales Q/Q", "SMA50", "Rel Volume", "Prev Close",
    "Employees", "LT Debt/Eq", "Earnings", "SMA200", "Avg Volume", "Price",
    "IPO", "Option/Short", "EPS/Sales Surpr.", "Trades", "Volume", "Change",
    "Sector", "Industry", "Description", "Name", "Exchange", "Country", "Currency"
]

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def normalize_lines(text):
    lines = []
    for line in str(text).replace("\r", "\n").split("\n"):
        line = line.strip()
        if line:
            lines.append(line)
    return lines

def parse_fundamental_text(text):
    lines = normalize_lines(text)
    out = {}
    i = 0

    while i < len(lines):
        key = lines[i]

        if key in KNOWN_KEYS:
            value = ""
            if i + 1 < len(lines):
                value = lines[i + 1]
            out[key] = value
            i += 2
            continue

        matched = False
        for known in sorted(KNOWN_KEYS, key=len, reverse=True):
            if key.startswith(known + " "):
                out[known] = key.replace(known, "", 1).strip()
                matched = True
                break

        if not matched:
            out.setdefault("_unparsed", []).append(key)

        i += 1

    return out

def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default

def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def save_manual_snapshot(ticker, raw_text):
    ticker = str(ticker).upper().strip()

    if not ticker:
        return {
            "status": "error",
            "error": "missing_ticker"
        }

    metrics = parse_fundamental_text(raw_text)

    raw_path = RAW_DIR / f"{ticker}.txt"
    raw_path.write_text(raw_text, encoding="utf-8")

    snapshots = load_json(SNAPSHOT_PATH, {})

    snapshots[ticker] = {
        "ticker": ticker,
        "source": "manual_dashboard_paste",
        "status": "ok",
        "updated_at": utc_now(),
        "metrics": metrics,
        "raw_text_path": str(raw_path)
    }

    save_json(SNAPSHOT_PATH, snapshots)

    attached = attach_snapshots_to_latest_candidates()

    return {
        "status": "complete",
        "ticker": ticker,
        "metric_count": len([k for k in metrics.keys() if not k.startswith("_")]),
        "unparsed_count": len(metrics.get("_unparsed", [])),
        "snapshot_path": str(SNAPSHOT_PATH),
        "raw_text_path": str(raw_path),
        "attached": attached
    }

def attach_snapshots_to_latest_candidates():
    snapshots = load_json(SNAPSHOT_PATH, {})

    if not LATEST_CANDIDATES.exists():
        return {
            "attached": 0,
            "reason": "latest_candidates_missing"
        }

    packet = load_json(LATEST_CANDIDATES, {})
    candidates = packet.get("top_candidates", [])

    attached = 0

    for c in candidates:
        ticker = str(c.get("ticker", "")).upper()
        snap = snapshots.get(ticker)

        if not snap:
            continue

        metrics = snap.get("metrics", {})
        if not metrics:
            continue

        c["fundamentals"] = metrics
        c["fundamental_snapshot"] = metrics
        c["fundamental_snapshot_source"] = snap.get("source")
        c["fundamental_snapshot_status"] = snap.get("status")
        c["fundamental_snapshot_updated_at"] = snap.get("updated_at")

        attached += 1

    packet["fundamental_snapshots_attached_at"] = utc_now()
    save_json(LATEST_CANDIDATES, packet)

    return {
        "attached": attached
    }

def list_available_snapshots():
    snapshots = load_json(SNAPSHOT_PATH, {})
    rows = []

    for ticker, snap in snapshots.items():
        metrics = snap.get("metrics", {})
        rows.append({
            "ticker": ticker,
            "source": snap.get("source"),
            "status": snap.get("status"),
            "updated_at": snap.get("updated_at"),
            "metric_count": len([k for k in metrics.keys() if not k.startswith("_")]),
            "unparsed_count": len(metrics.get("_unparsed", []))
        })

    return sorted(rows, key=lambda x: x.get("ticker", ""))

if __name__ == "__main__":
    print(json.dumps({
        "status": "ok",
        "snapshots": list_available_snapshots()
    }, indent=2, ensure_ascii=False))
