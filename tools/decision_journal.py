import os
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

def init_decision_tables():
    con = connect()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS decision_journal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT,
        timestamp TEXT,
        ticker TEXT,
        side TEXT,
        confidence REAL,
        allocation_pct REAL,
        regime TEXT,
        risk_level TEXT,
        final_action TEXT,
        approved_for_paper_trading INTEGER,
        approved_for_live_trading INTEGER,
        risk_overrides TEXT,
        summary TEXT,
        raw_json TEXT
    )
    """)

    con.commit()
    con.close()

def insert_decision(run_id, parsed, validation_result):
    init_decision_tables()

    summary = parsed.get("summary", {}) if isinstance(parsed, dict) else {}
    brief = summary.get("human_readable_brief", "") if isinstance(summary, dict) else ""

    trades = validation_result.get("validated_trades", [])

    con = connect()
    cur = con.cursor()

    if not trades:
        cur.execute(
            """
            INSERT INTO decision_journal (
                run_id, timestamp, ticker, side, confidence, allocation_pct,
                regime, risk_level, final_action, approved_for_paper_trading,
                approved_for_live_trading, risk_overrides, summary, raw_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                utc_now(),
                "",
                "",
                0.0,
                0.0,
                summary.get("regime", "unknown") if isinstance(summary, dict) else "unknown",
                summary.get("risk_level", "unknown") if isinstance(summary, dict) else "unknown",
                validation_result.get("final_action", "NO TRADE"),
                int(validation_result.get("approved_for_paper_trading", False)),
                int(validation_result.get("approved_for_live_trading", False)),
                json.dumps(validation_result.get("risk_overrides", [])),
                brief,
                json.dumps(validation_result, ensure_ascii=False)
            )
        )
    else:
        for t in trades:
            cur.execute(
                """
                INSERT INTO decision_journal (
                    run_id, timestamp, ticker, side, confidence, allocation_pct,
                    regime, risk_level, final_action, approved_for_paper_trading,
                    approved_for_live_trading, risk_overrides, summary, raw_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    utc_now(),
                    t.get("ticker", ""),
                    t.get("side", ""),
                    float(t.get("confidence", 0.0)),
                    float(t.get("allocation_pct", 0.0)),
                    t.get("regime", "unknown"),
                    t.get("risk_level", "unknown"),
                    t.get("final_action", validation_result.get("final_action", "NO TRADE")),
                    int(validation_result.get("approved_for_paper_trading", False)),
                    int(validation_result.get("approved_for_live_trading", False)),
                    json.dumps(validation_result.get("risk_overrides", [])),
                    brief,
                    json.dumps(validation_result, ensure_ascii=False)
                )
            )

    con.commit()
    con.close()

    return {
        "inserted": True,
        "run_id": run_id,
        "count": max(1, len(trades))
    }
