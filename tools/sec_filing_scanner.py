import os
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

TICKER_CIK_URL = "https://www.sec.gov/files/company_tickers.json"

def get_headers():
    user_agent = os.getenv("SEC_USER_AGENT", "Abe Park abe@example.com")
    return {"User-Agent": user_agent}

def get_ticker_map():
    r = requests.get(TICKER_CIK_URL, headers=get_headers(), timeout=20)
    r.raise_for_status()

    raw = r.json()
    out = {}

    for _, row in raw.items():
        ticker = row.get("ticker", "").upper()
        cik = str(row.get("cik_str", "")).zfill(10)
        title = row.get("title", "")
        out[ticker] = {"cik": cik, "title": title}

    return out

def run(symbols=None):
    symbols = symbols or ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN"]
    results = {}

    try:
        ticker_map = get_ticker_map()
    except Exception as e:
        return {
            "provider": "sec",
            "status": "ticker_map_failed",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    for symbol in symbols:
        try:
            symbol = symbol.upper()

            if symbol not in ticker_map:
                results[symbol] = {"error": "ticker_not_found"}
                continue

            cik = ticker_map[symbol]["cik"]
            url = f"https://data.sec.gov/submissions/CIK{cik}.json"

            r = requests.get(url, headers=get_headers(), timeout=20)
            r.raise_for_status()
            data = r.json()

            recent = data.get("filings", {}).get("recent", {})

            forms = recent.get("form", [])[:20]
            filing_dates = recent.get("filingDate", [])[:20]
            accession_numbers = recent.get("accessionNumber", [])[:20]
            primary_docs = recent.get("primaryDocument", [])[:20]

            filings = []

            for i in range(len(forms)):
                filings.append({
                    "form": forms[i],
                    "filingDate": filing_dates[i] if i < len(filing_dates) else "",
                    "accessionNumber": accession_numbers[i] if i < len(accession_numbers) else "",
                    "primaryDocument": primary_docs[i] if i < len(primary_docs) else ""
                })

            results[symbol] = {
                "cik": cik,
                "company": ticker_map[symbol]["title"],
                "recent_filings": filings
            }

        except Exception as e:
            results[symbol] = {"error": str(e)}

    return {
        "provider": "sec",
        "status": "ok",
        "filings": results,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
