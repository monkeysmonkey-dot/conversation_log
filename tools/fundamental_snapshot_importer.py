import json
import re
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
    "Sales", "P/B", "EPS next Y", "ROA", "Short Interest", "Perf YTD",
    "Book/sh", "P/C", "EPS next 5Y", "ROE", "52W High", "Perf Year",
    "Cash/sh", "P/FCF", "EPS past 3/5Y", "ROIC", "52W Low", "Perf 3Y",
    "Dividend Est.", "EV/EBITDA", "Sales past 3/5Y", "Gross Margin", "Volatility", "Perf 5Y",
    "Dividend TTM", "EV/Sales", "EPS Y/Y TTM", "Oper. Margin", "ATR (14)", "Perf 10Y",
    "Dividend Ex-Date", "Quick Ratio", "Sales Y/Y TTM", "Profit Margin", "RSI (14)", "Recom",
    "Dividend Gr. 3/5Y", "Current Ratio", "EPS Q/Q", "SMA20", "Beta", "Target Price",
    "Payout", "Debt/Eq", "Sales Q/Q", "SMA50", "Rel Volume", "Prev Close",
    "Employees", "LT Debt/Eq", "Earnings", "SMA200", "Avg Volume", "Price",
    "IPO", "Option/Short", "EPS/Sales Surpr.", "Trades", "Volume", "Change"
]

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def normalize_lines(text):
    lines = []
    for line in text.replace("\r", "\n").split("\n"):
        line = line.strip()
        if line:
            lines.append(line)
    return lines

def parse_finviz_style_text(text):
    """
    Parses copied Finviz-style two-column/flow text.
    The text often appears as alternating key/value lines.
    """
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
        else:
            # Fallback: detect "Key Value" same-line patterns.
            matched = False
            for known in sorted(KNOWN_KEYS, key=len, reverse=True):
                if key.startswith(known + " "):
                    out[known] = key.replace(known, "", 1).strip()
                    matched = True
                    break

            if not matched:
                # Preserve unknown fragments for debugging.
                out.setdefault("_unparsed", []).append(key)

            i += 1

    return out

def load_snapshots():
    try:
        return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_snapshots(data):
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def parse_raw_folder():
    snapshots = load_snapshots()

    parsed = []

    for path in RAW_DIR.glob("*.txt"):
        ticker = path.stem.upper()
        text = path.read_text(encoding="utf-8", errors="ignore")
        metrics = parse_finviz_style_text(text)

        snapshots[ticker] = {
            "ticker": ticker,
            "source": "manual_finviz_style_text",
            "parsed_at": utc_now(),
            "metrics": metrics
        }

        parsed.append(ticker)

    save_snapshots(snapshots)

    return {
        "parsed": parsed,
        "snapshot_path": str(SNAPSHOT_PATH)
    }

def attach_to_latest_candidates():
    snapshots = load_snapshots()

    if not LATEST_CANDIDATES.exists():
        return {
            "attached": 0,
            "error": "latest_candidates.json not found"
        }

    packet = json.loads(LATEST_CANDIDATES.read_text(encoding="utf-8"))
    candidates = packet.get("top_candidates", [])

    attached = 0

    for c in candidates:
        ticker = str(c.get("ticker", "")).upper()
        snap = snapshots.get(ticker)

        if not snap:
            continue

        metrics = snap.get("metrics", {})
        c["fundamentals"] = metrics
        c["fundamental_snapshot"] = metrics
        c["fundamental_snapshot_source"] = snap.get("source")
        c["fundamental_snapshot_updated_at"] = snap.get("parsed_at")

        attached += 1

    packet["fundamental_snapshots_attached_at"] = utc_now()
    LATEST_CANDIDATES.write_text(json.dumps(packet, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "attached": attached,
        "latest_candidates": str(LATEST_CANDIDATES)
    }

def main():
    parsed = parse_raw_folder()
    attached = attach_to_latest_candidates()

    print(json.dumps({
        "status": "complete",
        "parsed": parsed,
        "attached": attached
    }, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
