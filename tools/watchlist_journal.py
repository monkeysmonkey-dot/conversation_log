import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]
DB_PATH = BASE / "data" / "stock_manager.db"

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_watchlist_table():
    con = connect()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS watchlist_journal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT,
        timestamp TEXT,
        item TEXT,
        source TEXT,
        raw_json TEXT
    )
    """)

    cols = [r[1] for r in cur.execute("PRAGMA table_info(watchlist_journal)").fetchall()]

    if "ticker" not in cols:
        cur.execute("ALTER TABLE watchlist_journal ADD COLUMN ticker TEXT")

    if "action" not in cols:
        cur.execute("ALTER TABLE watchlist_journal ADD COLUMN action TEXT")

    if "reason" not in cols:
        cur.execute("ALTER TABLE watchlist_journal ADD COLUMN reason TEXT")

    con.commit()
    con.close()

def normalize_watchlist_item(item):
    if isinstance(item, dict):
        ticker = item.get("ticker", "")
        action = item.get("action", "")
        reason = item.get("reason", "")
        item_text = f"{ticker}_{action}: {reason}".strip("_: ")
        raw = item
    else:
        ticker = ""
        action = ""
        reason = str(item)
        item_text = str(item)
        raw = {"item": item}

    return {
        "ticker": str(ticker).upper(),
        "action": str(action).upper(),
        "reason": str(reason),
        "item_text": item_text,
        "raw": raw
    }

def insert_watchlist_updates(run_id, parsed):
    init_watchlist_table()

    summary = parsed.get("summary", {}) if isinstance(parsed, dict) else {}
    updates = summary.get("watchlist_updates", []) if isinstance(summary, dict) else []

    if not isinstance(updates, list):
        updates = []

    con = connect()
    cur = con.cursor()

    inserted = 0

    for item in updates:
        norm = normalize_watchlist_item(item)

        cur.execute(
            """
            INSERT INTO watchlist_journal (
                run_id, timestamp, item, source, raw_json, ticker, action, reason
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                utc_now(),
                norm["item_text"],
                "hermes_summary",
                json.dumps(norm["raw"], ensure_ascii=False),
                norm["ticker"],
                norm["action"],
                norm["reason"]
            )
        )

        inserted += 1

    con.commit()
    con.close()

    return {
        "inserted": inserted,
        "run_id": run_id
    }
