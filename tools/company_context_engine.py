import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]
MAP_PATH = BASE / "config" / "company_context_map.json"
LATEST = BASE / "features" / "latest_candidates.json"

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default

def safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default

def infer_flow_interpretation(candidate):
    trend = safe_float(candidate.get("trend_score"))
    rs = safe_float(candidate.get("relative_strength_vs_spy"))
    vol = safe_float(candidate.get("volume_ratio"))
    rank_change = candidate.get("rank_change")
    whale = str(candidate.get("whale_signal", "")).lower()
    sentiment = str(candidate.get("qualitative_sentiment", "")).lower()

    panic_selling = False
    dip_buying = False
    institutional_buying = "unknown"
    smart_money_signal = "unknown"
    retail_fomo_signal = "unknown"

    if trend < -3 and vol >= 1.2:
        panic_selling = True

    if trend > 5 and rs > 0 and vol >= 1.0:
        dip_buying = True

    if "buy" in whale:
        institutional_buying = "possible"
        smart_money_signal = "possible"

    if trend >= 10 and vol >= 1.5 and sentiment == "positive":
        retail_fomo_signal = "possible"

    if trend >= 10 and vol < 1:
        retail_fomo_signal = "not_confirmed"
        smart_money_signal = "not_confirmed"

    return {
        "panic_selling": panic_selling,
        "dip_buying": dip_buying,
        "institutional_buying": institutional_buying,
        "smart_money_signal": smart_money_signal,
        "retail_fomo_signal": retail_fomo_signal,
        "interpretation": build_flow_interpretation_text(trend, rs, vol, whale, sentiment)
    }

def build_flow_interpretation_text(trend, rs, vol, whale, sentiment):
    parts = []

    if trend >= 10 and rs > 0:
        parts.append("Strong trend with positive relative strength suggests leadership.")
    elif trend >= 5:
        parts.append("Trend is constructive but not dominant.")
    elif trend < 0:
        parts.append("Trend is weak or deteriorating.")

    if vol >= 1.2:
        parts.append("Volume is confirming participation.")
    elif vol >= 1.0:
        parts.append("Volume is acceptable but not unusually strong.")
    else:
        parts.append("Volume is thin, so confirmation is incomplete.")

    if "buy" in whale:
        parts.append("Whale/insider buying may indicate informed accumulation.")
    elif "sell" in whale:
        parts.append("Whale/insider selling may indicate distribution or risk reduction.")
    else:
        parts.append("No confirmed smart-money transaction signal yet.")

    if sentiment == "positive":
        parts.append("Narrative support is positive.")
    elif sentiment == "missing":
        parts.append("Narrative confirmation is missing.")
    elif sentiment == "negative":
        parts.append("Narrative tone is negative.")

    return " ".join(parts)

def infer_supply_demand_read(context, candidate):
    status = context.get("supply_demand_status", "unknown")
    vol = safe_float(candidate.get("volume_ratio"))

    if "shortage" in status:
        read = "Bullish if demand remains strong, but risk rises if customers slow capex or shortages turn into overcapacity."
    elif "oversupply" in status:
        read = "Bearish or cautious unless pricing stabilizes and inventories normalize."
    elif "balanced" in status:
        read = "Neutral; needs company-specific or theme-specific catalyst."
    else:
        read = "Supply/demand status is not confirmed yet."

    if vol < 1:
        read += " Current volume is thin, so market confirmation is incomplete."

    return read

def enrich_company_context(candidate_packet):
    if not isinstance(candidate_packet, dict):
        return candidate_packet

    context_map = load_json(MAP_PATH, {})
    candidates = candidate_packet.get("top_candidates", [])

    for c in candidates:
        ticker = c.get("ticker")
        base_context = context_map.get(ticker, {})

        market_structure = base_context.get("market_structure", {})

        context = {
            "market_structure": market_structure,
            "what_company_provides": base_context.get("what_company_provides", "Unknown"),
            "key_products_services": base_context.get("key_products_services", []),
            "known_customers_or_end_markets": base_context.get("known_customers_or_end_markets", []),
            "contracts_or_relationships": base_context.get("contracts_or_relationships", []),
            "who_they_supply": base_context.get("who_they_supply", []),
            "supply_demand_status": base_context.get("supply_demand_status", "unknown"),
            "supply_demand_read": infer_supply_demand_read(base_context, c),
            "innovation_moat": base_context.get("innovation_moat", "Unknown"),
            "sector_critical_role": base_context.get("sector_critical_role", "Unknown"),
            "momentum_driver": base_context.get("momentum_driver", "Unknown"),
            "positive_case": base_context.get("positive_case", []),
            "weaknesses": base_context.get("weaknesses", []),
            "critical_bullish_factors": base_context.get("critical_bullish_factors", []),
            "critical_bearish_factors": base_context.get("critical_bearish_factors", []),
            "flow_interpretation": infer_flow_interpretation(c)
        }

        c["company_context"] = context

    candidate_packet["company_context_enriched_at"] = utc_now()

    LATEST.parent.mkdir(parents=True, exist_ok=True)
    LATEST.write_text(json.dumps(candidate_packet, indent=2, ensure_ascii=False), encoding="utf-8")

    return candidate_packet

if __name__ == "__main__":
    packet = load_json(LATEST, {})
    packet = enrich_company_context(packet)
    print(json.dumps({
        "status": "complete",
        "candidates": len(packet.get("top_candidates", [])),
        "latest": str(LATEST)
    }, indent=2))
