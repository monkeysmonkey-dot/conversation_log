import os
import re
import json
import time
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

BASE = Path(__file__).resolve().parents[1]
CACHE_DIR = BASE / "qualitative" / "official" / "sec" / "form4_detail_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

TICKER_CIK_URL = "https://www.sec.gov/files/company_tickers.json"

TRANSACTION_MAP = {
    "P": {"direction": "buy", "type": "open_market_purchase", "base_score": 40},
    "S": {"direction": "sell", "type": "open_market_sale", "base_score": -18},
    "A": {"direction": "acquisition", "type": "grant_or_award", "base_score": 5},
    "F": {"direction": "sell", "type": "tax_withholding", "base_score": -3},
    "M": {"direction": "exercise", "type": "option_exercise_or_conversion", "base_score": 4},
    "G": {"direction": "transfer", "type": "gift", "base_score": 0},
    "D": {"direction": "sell", "type": "disposition_to_issuer", "base_score": -5},
    "J": {"direction": "other", "type": "other", "base_score": 0}
}

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def headers():
    return {
        "User-Agent": os.getenv("SEC_USER_AGENT", "Abe Park contact@example.com"),
        "Accept-Encoding": "gzip, deflate"
    }

def safe_float(x, default=0.0):
    try:
        return float(str(x).replace(",", "").strip())
    except Exception:
        return default

def clean_cik(cik):
    return str(cik).lstrip("0")

def accession_no_dash(accession):
    return str(accession).replace("-", "")

def get_text(node, path, default=""):
    found = node.find(path)
    if found is not None and found.text is not None:
        return found.text.strip()
    return default

def get_ticker_map():
    cache = CACHE_DIR / "company_tickers.json"

    if cache.exists():
        try:
            return json.loads(cache.read_text(encoding="utf-8"))
        except Exception:
            pass

    r = requests.get(TICKER_CIK_URL, headers=headers(), timeout=8)
    r.raise_for_status()
    raw = r.json()

    out = {}

    for _, row in raw.items():
        ticker = row.get("ticker", "").upper()
        cik = str(row.get("cik_str", "")).zfill(10)
        title = row.get("title", "")
        out[ticker] = {"cik": cik, "title": title}

    cache.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out

def classify_actor(owner_name, relationship):
    name_l = str(owner_name).lower()

    is_director = relationship.get("is_director")
    is_officer = relationship.get("is_officer")
    is_ten_pct = relationship.get("is_ten_percent_owner")
    officer_title = relationship.get("officer_title", "")

    institutional_words = [
        "capital", "management", "partners", "advisors", "advisor",
        "fund", "asset", "investments", "holdings", "lp", "llc", "inc"
    ]

    if is_officer:
        return "officer"
    if is_director:
        return "director"
    if is_ten_pct and any(w in name_l for w in institutional_words):
        return "institutional_10pct_owner"
    if is_ten_pct:
        return "10pct_owner"
    if any(w in name_l for w in institutional_words):
        return "institution_or_fund"
    if officer_title:
        return "officer"
    return "insider"

def role_weight(actor_type, officer_title):
    title_l = str(officer_title).lower()

    if "chief executive" in title_l or title_l == "ceo":
        return 18
    if "chief financial" in title_l or title_l == "cfo":
        return 15
    if "chief operating" in title_l or title_l == "coo":
        return 12
    if actor_type == "officer":
        return 10
    if actor_type == "director":
        return 8
    if actor_type in ["10pct_owner", "institutional_10pct_owner"]:
        return 12
    if actor_type == "institution_or_fund":
        return 8
    return 4

def value_weight(value):
    value = abs(safe_float(value))

    if value >= 10_000_000:
        return 20
    if value >= 5_000_000:
        return 16
    if value >= 1_000_000:
        return 12
    if value >= 250_000:
        return 8
    if value >= 50_000:
        return 4
    return 1

def pct_holding_weight(shares, post_shares):
    shares = abs(safe_float(shares))
    post = abs(safe_float(post_shares))

    if post <= 0:
        return 0

    pct = shares / post

    if pct >= 0.25:
        return 18
    if pct >= 0.10:
        return 12
    if pct >= 0.05:
        return 8
    if pct >= 0.01:
        return 4
    return 1

def score_transaction(code, estimated_value, actor_type, officer_title, shares, post_shares):
    info = TRANSACTION_MAP.get(code, {"direction": "unknown", "type": "unknown", "base_score": 0})
    base = info["base_score"]

    score = base
    score += role_weight(actor_type, officer_title)
    score += value_weight(estimated_value)
    score += pct_holding_weight(shares, post_shares)

    # Routine/low-signal transaction caps.
    if code in ["A", "F", "M", "G"]:
        score = min(score, 35)

    # Open-market sell can be meaningful but not as clean as purchase.
    if code == "S":
        score = abs(score)
        score = min(score, 65)

    # Open-market purchase can be high conviction.
    if code == "P":
        score = min(max(score, 0), 100)

    return round(min(max(abs(score), 0), 100), 1)

def parse_bool(text):
    return str(text).strip().lower() in ["1", "true", "yes"]

def parse_form4_xml(xml_text, ticker, filing_meta):
    root = ET.fromstring(xml_text)

    issuer_symbol = get_text(root, "./issuer/issuerTradingSymbol", ticker).upper()
    filing_date = filing_meta.get("filingDate", "")

    owner_name = get_text(root, "./reportingOwner/reportingOwnerId/rptOwnerName", "")
    relationship_node = root.find("./reportingOwner/reportingOwnerRelationship")

    relationship = {
        "is_director": False,
        "is_officer": False,
        "is_ten_percent_owner": False,
        "officer_title": ""
    }

    if relationship_node is not None:
        relationship = {
            "is_director": parse_bool(get_text(relationship_node, "./isDirector", "")),
            "is_officer": parse_bool(get_text(relationship_node, "./isOfficer", "")),
            "is_ten_percent_owner": parse_bool(get_text(relationship_node, "./isTenPercentOwner", "")),
            "officer_title": get_text(relationship_node, "./officerTitle", "")
        }

    actor_type = classify_actor(owner_name, relationship)

    transactions = []

    for tx in root.findall(".//nonDerivativeTransaction"):
        code = get_text(tx, "./transactionCoding/transactionCode", "")
        tx_date = get_text(tx, "./transactionDate/value", "")
        shares = safe_float(get_text(tx, "./transactionAmounts/transactionShares/value", "0"))
        price = safe_float(get_text(tx, "./transactionAmounts/transactionPricePerShare/value", "0"))
        post_shares = safe_float(get_text(tx, "./postTransactionAmounts/sharesOwnedFollowingTransaction/value", "0"))
        ownership = get_text(tx, "./ownershipNature/directOrIndirectOwnership/value", "")

        estimated_value = shares * price if shares and price else 0.0

        info = TRANSACTION_MAP.get(code, {
            "direction": "unknown",
            "type": "unknown",
            "base_score": 0
        })

        conviction_score = score_transaction(
            code,
            estimated_value,
            actor_type,
            relationship.get("officer_title", ""),
            shares,
            post_shares
        )

        transactions.append({
            "ticker": issuer_symbol or ticker,
            "owner": owner_name,
            "actor_type": actor_type,
            "is_director": relationship.get("is_director"),
            "is_officer": relationship.get("is_officer"),
            "is_ten_percent_owner": relationship.get("is_ten_percent_owner"),
            "officer_title": relationship.get("officer_title"),
            "transaction_code": code,
            "transaction_type": info.get("type"),
            "direction": info.get("direction"),
            "shares": shares,
            "price": price,
            "estimated_value": round(estimated_value, 2),
            "post_transaction_shares": post_shares,
            "ownership": ownership,
            "transaction_date": tx_date,
            "filing_date": filing_date,
            "source_form": filing_meta.get("form", "4"),
            "accessionNumber": filing_meta.get("accessionNumber", ""),
            "primaryDocument": filing_meta.get("primaryDocument", ""),
            "conviction_score": conviction_score
        })

    return transactions

def fetch_form4_xml(ticker, filing_meta):
    ticker_map = get_ticker_map()

    if ticker.upper() not in ticker_map:
        return []

    cik = ticker_map[ticker.upper()]["cik"]
    cik_clean = clean_cik(cik)
    accession = filing_meta.get("accessionNumber", "")
    primary_doc = filing_meta.get("primaryDocument", "")

    if not accession or not primary_doc:
        return []

    cache_key = f"{ticker}_{accession_no_dash(accession)}.json"
    cache_path = CACHE_DIR / cache_key

    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    url = f"https://www.sec.gov/Archives/edgar/data/{cik_clean}/{accession_no_dash(accession)}/{primary_doc}"

    try:
        r = requests.get(url, headers=headers(), timeout=8)
        r.raise_for_status()

        transactions = parse_form4_xml(r.text, ticker.upper(), filing_meta)
        cache_path.write_text(json.dumps(transactions, indent=2, ensure_ascii=False), encoding="utf-8")

        time.sleep(0.2)
        return transactions

    except Exception as e:
        error_payload = [{
            "ticker": ticker.upper(),
            "error": str(e)[:300],
            "source_form": filing_meta.get("form", "4"),
            "accessionNumber": accession
        }]
        cache_path.write_text(json.dumps(error_payload, indent=2), encoding="utf-8")
        return error_payload

def get_form4_details_for_ticker(ticker, filings, max_filings=3):
    details = []

    if not isinstance(filings, list):
        return details

    form4s = [f for f in filings if isinstance(f, dict) and f.get("form") == "4"]

    for f in form4s[:max_filings]:
        details.extend(fetch_form4_xml(ticker, f))

    return details

if __name__ == "__main__":
    import sys
    ticker = sys.argv[1].upper() if len(sys.argv) > 1 else "AAPL"
    print(json.dumps({
        "ticker": ticker,
        "note": "Use get_form4_details_for_ticker(ticker, filings) from candidate_preranker."
    }, indent=2))
