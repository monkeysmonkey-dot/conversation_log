import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]
DB_PATH = BASE / "data" / "stock_manager.db"

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    con = connect()
    cur = con.cursor()

    cur.execute('''
    CREATE TABLE IF NOT EXISTS runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT UNIQUE,
        timestamp TEXT,
        mode TEXT,
        status TEXT,
        summary TEXT,
        raw_json TEXT
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS tool_calls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT,
        timestamp TEXT,
        tool_name TEXT,
        status TEXT,
        payload TEXT
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        event_type TEXT,
        symbol TEXT,
        title TEXT,
        description TEXT,
        payload TEXT
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS thesis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        symbol TEXT,
        thesis_status TEXT,
        title TEXT,
        thesis_text TEXT,
        confidence REAL,
        payload TEXT
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        report_type TEXT,
        path TEXT,
        summary TEXT
    )
    ''')

    cur.execute('''
    CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
        title,
        body,
        source,
        timestamp
    )
    ''')

    con.commit()
    con.close()

def insert_run(run_id, mode, status, summary, raw):
    con = connect()
    cur = con.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO runs (run_id, timestamp, mode, status, summary, raw_json) VALUES (?, ?, ?, ?, ?, ?)",
        (run_id, utc_now(), mode, status, summary, json.dumps(raw, ensure_ascii=False))
    )
    con.commit()
    con.close()

def insert_tool_call(run_id, tool_name, status, payload):
    con = connect()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO tool_calls (run_id, timestamp, tool_name, status, payload) VALUES (?, ?, ?, ?, ?)",
        (run_id, utc_now(), tool_name, status, json.dumps(payload, ensure_ascii=False))
    )
    con.commit()
    con.close()

def insert_fts(title, body, source):
    con = connect()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO memory_fts (title, body, source, timestamp) VALUES (?, ?, ?, ?)",
        (title, body, source, utc_now())
    )
    con.commit()
    con.close()

if __name__ == "__main__":
    init_db()
    print(f"SQLite memory initialized at: {DB_PATH}")
