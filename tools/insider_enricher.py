import json
from pathlib import Path
from datetime import datetime, timezone

from sec_form4_detail_scanner import get_form4_details_for_ticker

BASE = Path(__file__).resolve().parents[1]
LATEST_CANDIDATES = BASE / "features" / "latest_candidates.json"

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default

def summarize_insider_transactions(transactions):
    clean = []
    net_value = 0.0
    max_conviction = 0.0
    buy_value = 0.0
    sell_value = 0.0
    buy_count = 0
    sell_count = 0

    for tx in transactions:
        if not isinstance(tx, dict):
            continue

        if tx.get("error"):
            continue

        direction = str(tx.get("direction", "")).lower()
        estimated_value = safe_float(tx.get("estimated_value"))
        conviction = safe_float(tx.get("conviction_score"))

        if direction == "buy":
            net_value += estimated_value
            buy_value += estimated_value
            buy_count += 1
        elif direction == "sell":
            net_value -= estimated_value
            sell_value += estimated_value
            sell_count += 1

        max_conviction = max(max_conviction, conviction)

        clean.append({
            "ticker": tx.get("ticker"),
            "owner": tx.get("owner"),
            "actor_type": tx.get("actor_type"),
            "officer_title": tx.get("officer_title"),
            "transaction_code": tx.get("transaction_code"),
            "transaction_type": tx.get("transaction_type"),
            "direction": tx.get("direction"),
            "shares": tx.get("shares"),
            "price": tx.get("price"),
            "estimated_value": tx.get("estimated_value"),
            "transaction_date": tx.get("transaction_date"),
            "filing_date": tx.get("filing_date"),
            "source_form": tx.get("source_form"),
            "conviction_score": tx.get("conviction_score")
        })

    if buy_count > 0 and sell_count == 0:
        signal = "net_insider_buying"
    elif sell_count > 0 and buy_count == 0:
        signal = "net_insider_selling"
    elif buy_count > 0 and sell_count > 0:
        signal = "mixed_insider_activity"
    else:
        signal = "none"

    return {
        "signal": signal,
        "insider_detail": clean[:10],
        "insider_net_estimated_value": round(net_value, 2),
        "insider_buy_estimated_value": round(buy_value, 2),
        "insider_sell_estimated_value": round(sell_value, 2),
        "insider_buy_count": buy_count,
        "insider_sell_count": sell_count,
        "insider_max_transaction_conviction": round(max_conviction, 1)
    }

def get_filings_for_ticker(ticker, qualitative_data):
    sec = qualitative_data.get("sec_filings", {}) if isinstance(qualitative_data, dict) else {}
    filings = sec.get("recent_material_filings", {}) if isinstance(sec, dict) else {}
    rows = filings.get(ticker, [])
    return rows if isinstance(rows, list) else []

def enrich_candidate_packet_with_insider_details(candidate_packet, qualitative_data):
    if not isinstance(candidate_packet, dict):
        return candidate_packet

    candidates = candidate_packet.get("top_candidates", [])

    if not isinstance(candidates, list):
        return candidate_packet

    for c in candidates:
        ticker = c.get("ticker", "")

        if not ticker:
            continue

        filings = get_filings_for_ticker(ticker, qualitative_data)

        forms = []
        for row in filings[:10]:
            if isinstance(row, dict):
                forms.append(row.get("form", ""))

        transactions = get_form4_details_for_ticker(ticker, filings, max_filings=3)
        summary = summarize_insider_transactions(transactions)

        existing_signal = c.get("whale_signal", "none")

        if summary["signal"] != "none":
            c["whale_signal"] = summary["signal"]
        else:
            c["whale_signal"] = existing_signal

        c["filing_forms"] = forms or c.get("filing_forms", [])
        c["insider_detail"] = summary["insider_detail"]
        c["insider_net_estimated_value"] = summary["insider_net_estimated_value"]
        c["insider_buy_estimated_value"] = summary["insider_buy_estimated_value"]
        c["insider_sell_estimated_value"] = summary["insider_sell_estimated_value"]
        c["insider_buy_count"] = summary["insider_buy_count"]
        c["insider_sell_count"] = summary["insider_sell_count"]
        c["insider_max_transaction_conviction"] = summary["insider_max_transaction_conviction"]

        if summary["insider_detail"]:
            extra_reason = (
                f" insider {summary['signal']}, "
                f"net ${summary['insider_net_estimated_value']:,.0f}, "
                f"max tx conviction {summary['insider_max_transaction_conviction']}"
            )
            c["reason"] = str(c.get("reason", "")) + "," + extra_reason

    candidate_packet["top_candidates"] = candidates
    candidate_packet["insider_enriched_at"] = utc_now()

    LATEST_CANDIDATES.parent.mkdir(parents=True, exist_ok=True)
    LATEST_CANDIDATES.write_text(json.dumps(candidate_packet, indent=2, ensure_ascii=False), encoding="utf-8")

    return candidate_packet
