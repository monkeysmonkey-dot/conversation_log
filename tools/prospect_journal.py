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

def init_prospect_table():
    con = connect()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS prospect_journal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT,
        timestamp TEXT,
        rank INTEGER,
        rank_change TEXT,
        ticker TEXT,
        candidate_score REAL,
        conviction_rate REAL,
        trend_score REAL,
        relative_strength_vs_spy REAL,
        volume_ratio REAL,
        volume_ramp TEXT,
        macro_alignment TEXT,
        whale_signal TEXT,
        policy_geo_risk TEXT,
        qualitative_sentiment TEXT,
        reason TEXT,
        report_path TEXT,
        raw_json TEXT
    )
    """)

    con.commit()
    con.close()

def insert_prospects(run_id, candidate_packet):
    init_prospect_table()

    candidates = candidate_packet.get("top_candidates", []) if isinstance(candidate_packet, dict) else []

    con = connect()
    cur = con.cursor()

    inserted = 0

    for c in candidates:
        cur.execute("""
        INSERT INTO prospect_journal (
            run_id, timestamp, rank, rank_change, ticker,
            candidate_score, conviction_rate, trend_score,
            relative_strength_vs_spy, volume_ratio, volume_ramp,
            macro_alignment, whale_signal, policy_geo_risk,
            qualitative_sentiment, reason, report_path, raw_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            utc_now(),
            c.get("rank"),
            str(c.get("rank_change")),
            c.get("ticker"),
            float(c.get("candidate_score", 0.0)),
            float(c.get("conviction_rate", 0.0)),
            float(c.get("trend_score", 0.0)),
            float(c.get("relative_strength_vs_spy", 0.0)),
            float(c.get("volume_ratio", 0.0)),
            c.get("volume_ramp", ""),
            c.get("macro_alignment", ""),
            c.get("whale_signal", ""),
            c.get("policy_geo_risk", ""),
            c.get("qualitative_sentiment", ""),
            c.get("reason", ""),
            c.get("detailed_report", ""),
            json.dumps(c, ensure_ascii=False)
        ))
        inserted += 1

    con.commit()
    con.close()

    return {
        "inserted": inserted,
        "run_id": run_id
    }
