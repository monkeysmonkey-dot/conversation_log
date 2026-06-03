import os
import csv
import sqlite3
from datetime import datetime

DB_PATH = r"C:\zeroclaw\Storage\master_portfolio.db"
WORKSPACE_DIR = r"C:\zeroclaw\Workspace\stock_manager"

def initialize_database_schemas():
    """Ensure persistence ledger tables match structural data matrices precisely."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_core (
            ticker TEXT PRIMARY KEY,
            shares REAL,
            avg_cost REAL,
            last_updated TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS watchlist_core (
            ticker TEXT PRIMARY KEY,
            target_price REAL,
            notes TEXT,
            last_updated TEXT
        )
    """)
    conn.commit()
    conn.close()

def ingest_portfolio_csv():
    """Parse, clean, and upsert raw portfolio CSV structures into the core database."""
    csv_path = os.path.join(WORKSPACE_DIR, "portfolio.csv")
    if not os.path.exists(csv_path):
        print(f"[WARN] Target portfolio file not found at: {csv_path}. Skipping.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()

    with open(csv_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ticker = row["ticker"].strip().upper()
            shares = float(row["shares"])
            avg_cost = float(row["avg_cost"])
            
            cursor.execute("""
                INSERT INTO portfolio_core (ticker, shares, avg_cost, last_updated)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(ticker) DO UPDATE SET
                    shares = excluded.shares,
                    avg_cost = excluded.avg_cost,
                    last_updated = excluded.last_updated
            """, (ticker, shares, avg_cost, timestamp))
            print(f"[PORTFOLIO_INGEST] Upserted core holding: {ticker} | {shares} shares")
    conn.commit()
    conn.close()

def ingest_watchlist_csv():
    """Parse, clean, and upsert target watchlist assets into the tracking database."""
    csv_path = os.path.join(WORKSPACE_DIR, "watchlist.csv")
    if not os.path.exists(csv_path):
        print(f"[WARN] Target watchlist file not found at: {csv_path}. Skipping.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()

    with open(csv_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ticker = row["ticker"].strip().upper()
            target_price = float(row["target_price"]) if row.get("target_price") else 0.0
            notes = row.get("notes", "").strip()
            
            cursor.execute("""
                INSERT INTO watchlist_core (ticker, target_price, notes, last_updated)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(ticker) DO UPDATE SET
                    target_price = excluded.target_price,
                    notes = excluded.notes,
                    last_updated = excluded.last_updated
            """, (ticker, target_price, notes, timestamp))
            print(f"[WATCHLIST_INGEST] Upserted tracking target: {ticker} | Target: ${target_price}")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    print("[QUANT_INGEST] Initializing production parsing pipelines...")
    initialize_database_schemas()
    ingest_portfolio_csv()
    ingest_watchlist_csv()
    print("[QUANT_INGEST] Pipeline loop execution successfully wrapped up with zero errors.")