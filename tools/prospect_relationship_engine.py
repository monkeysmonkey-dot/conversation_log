import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]
MAP_PATH = BASE / "config" / "prospect_relationship_map.json"

DEFAULT_MAP = {
    "AAPL": {
        "sector_leader": "QQQ",
        "primary_theme": "consumer_ai_edge_devices",
        "move_logic": "company_leadership_with_theme_support",
        "theme_chain": ["AI software", "edge devices", "services ecosystem", "semiconductor demand", "supply chain"],
        "upstream": ["TSM", "NVDA", "AVGO", "QCOM", "ARM"],
        "downstream": ["APP", "SHOP", "ADBE"],
        "adjacent": ["MSFT", "GOOGL", "META", "AMZN"],
        "competitors": ["MSFT", "GOOGL", "META", "AMZN"],
        "inverse_competitors": [],
        "economic_transmission": "AI-enabled devices and services can increase semiconductor demand, cloud usage, app ecosystem activity, and consumer upgrade cycles."
    },
    "NVDA": {
        "sector_leader": "SMH",
        "primary_theme": "ai_compute_infrastructure",
        "move_logic": "theme_leader",
        "theme_chain": ["AI capex", "compute", "GPU", "HBM memory", "networking", "data centers", "power demand", "nuclear/uranium", "critical minerals"],
        "upstream": ["TSM", "ASML", "AMAT", "LRCX", "KLAC", "MU", "ARM"],
        "downstream": ["MSFT", "AMZN", "GOOGL", "META", "ORCL"],
        "adjacent": ["AVGO", "AMD", "ANET", "MRVL", "CSCO", "INTC"],
        "competitors": ["AMD", "INTC"],
        "inverse_competitors": [],
        "economic_transmission": "AI compute demand can increase data center capex, networking demand, HBM demand, power demand, grid stress, cooling needs, and semiconductor equipment demand."
    },
    "QQQ": {
        "sector_leader": "SPY",
        "primary_theme": "broad_technology_momentum",
        "move_logic": "broad_theme_proxy",
        "theme_chain": ["mega-cap tech", "AI capex", "software/platforms", "semiconductors", "market liquidity"],
        "upstream": ["NVDA", "AVGO", "MSFT", "AMZN", "GOOGL", "META"],
        "downstream": ["XLK", "SMH", "IGV"],
        "adjacent": ["SPY", "IWM"],
        "competitors": [],
        "inverse_competitors": [],
        "economic_transmission": "Broad technology momentum can indicate risk appetite, liquidity preference, growth-sector leadership, and market breadth conditions."
    },
    "TSLA": {
        "sector_leader": "QQQ",
        "primary_theme": "ev_autonomy_energy_storage",
        "move_logic": "high_beta_theme_candidate",
        "theme_chain": ["EV demand", "autonomy", "battery supply chain", "lithium/minerals", "grid/power storage"],
        "upstream": ["ALB", "LAC", "NVDA", "ON", "TSM"],
        "downstream": ["charging infrastructure", "energy storage", "robotics/autonomy ecosystem"],
        "adjacent": ["RIVN", "LCID", "GM", "F"],
        "competitors": ["RIVN", "LCID", "GM", "F"],
        "inverse_competitors": [],
        "economic_transmission": "EV/autonomy momentum connects to battery materials, power electronics, charging, grid storage, and AI inference hardware."
    },
    "MSFT": {
        "sector_leader": "QQQ",
        "primary_theme": "enterprise_ai_cloud",
        "move_logic": "platform_leader",
        "theme_chain": ["AI software", "cloud capex", "data centers", "GPU demand", "power demand", "enterprise productivity"],
        "upstream": ["NVDA", "AMD", "AVGO", "ANET", "MU"],
        "downstream": ["NOW", "CRM", "ADBE", "PANW"],
        "adjacent": ["AMZN", "GOOGL", "ORCL"],
        "competitors": ["AMZN", "GOOGL", "ORCL"],
        "inverse_competitors": [],
        "economic_transmission": "Enterprise AI/cloud growth increases data center capex, software productivity adoption, GPU/networking demand, and power infrastructure pressure."
    },
    "LLY": {
        "sector_leader": "XLV",
        "primary_theme": "glp1_obesity_diabetes",
        "move_logic": "drug_class_leader_or_competitor_share_shift",
        "theme_chain": ["GLP-1 demand", "obesity/diabetes treatment", "drug capacity", "payer coverage", "consumer health shift"],
        "upstream": ["contract manufacturing", "fill-finish capacity", "specialty ingredients"],
        "downstream": ["pharmacies", "managed care", "medical device monitoring"],
        "adjacent": ["NVO", "AMGN", "PFE"],
        "competitors": ["NVO"],
        "inverse_competitors": ["NVO"],
        "economic_transmission": "A drug-specific win can help the class but may hurt direct share competitors if the market reads it as share capture."
    },
    "NVO": {
        "sector_leader": "XLV",
        "primary_theme": "glp1_obesity_diabetes",
        "move_logic": "drug_class_leader_or_competitor_share_shift",
        "theme_chain": ["GLP-1 demand", "obesity/diabetes treatment", "drug capacity", "payer coverage", "consumer health shift"],
        "upstream": ["contract manufacturing", "fill-finish capacity", "specialty ingredients"],
        "downstream": ["pharmacies", "managed care", "medical device monitoring"],
        "adjacent": ["LLY", "AMGN", "PFE"],
        "competitors": ["LLY"],
        "inverse_competitors": ["LLY"],
        "economic_transmission": "A drug-specific win can help the class but may hurt direct share competitors if the market reads it as share capture."
    }
}

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def ensure_map():
    MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not MAP_PATH.exists():
        MAP_PATH.write_text(json.dumps(DEFAULT_MAP, indent=2), encoding="utf-8")
    try:
        return json.loads(MAP_PATH.read_text(encoding="utf-8"))
    except Exception:
        return DEFAULT_MAP

def safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default

def infer_theme_phase(candidate):
    conviction = safe_float(candidate.get("conviction_rate"))
    trend = safe_float(candidate.get("trend_score"))
    vol = safe_float(candidate.get("volume_ratio"))
    sentiment = candidate.get("qualitative_sentiment")
    macro = candidate.get("macro_alignment")

    if trend >= 10 and vol < 1 and sentiment == "missing":
        phase = "early_or_unconfirmed_momentum"
        consensus = "not_confirmed"
        bubble_risk = "low_to_medium"
        interpretation = "Price leadership exists, but participation and narrative confirmation are not mature yet."
    elif trend >= 10 and vol >= 1.2:
        phase = "momentum_expansion"
        consensus = "rising"
        bubble_risk = "medium"
        interpretation = "Trend and participation are aligned. This can indicate a stronger wave, but crowding must be monitored."
    elif conviction >= 80 and sentiment == "positive":
        phase = "consensus_build"
        consensus = "rising"
        bubble_risk = "medium"
        interpretation = "Strong score and positive narrative suggest consensus may be forming."
    elif trend < 5:
        phase = "lagging_or_base_building"
        consensus = "weak"
        bubble_risk = "low"
        interpretation = "The setup is not leading yet. It may be basing, lagging, or waiting for confirmation."
    else:
        phase = "watchlist_confirmation_needed"
        consensus = "unclear"
        bubble_risk = "unknown"
        interpretation = "The setup needs more evidence from volume, catalysts, sentiment, or related names."

    if macro == "unfavorable":
        recession_sensitivity = "high"
    elif macro == "supportive":
        recession_sensitivity = "low_to_medium"
    else:
        recession_sensitivity = "medium"

    return {
        "phase": phase,
        "consensus": consensus,
        "bubble_risk": bubble_risk,
        "recession_sensitivity": recession_sensitivity,
        "interpretation": interpretation
    }

def compare_to_sector_leader(candidate, candidate_lookup, relationship_map):
    ticker = candidate.get("ticker")
    rel = relationship_map.get(ticker, {})
    leader = rel.get("sector_leader", "")
    leader_obj = candidate_lookup.get(leader)

    if not leader:
        return {
            "leader": "",
            "relative_setup": "no_leader_mapped",
            "interpretation": "No sector leader mapping configured yet."
        }

    if not leader_obj:
        return {
            "leader": leader,
            "relative_setup": "leader_not_in_current_candidate_set",
            "interpretation": f"{leader} is mapped as comparison leader, but it is not in the current candidate packet. Add it to scan universe for direct comparison."
        }

    score = safe_float(candidate.get("candidate_score"))
    leader_score = safe_float(leader_obj.get("candidate_score"))

    if score > leader_score:
        setup = "outperforming_leader"
        interp = f"{ticker} candidate score is above {leader}. This points to possible company-specific leadership."
    elif score < leader_score:
        setup = "lagging_leader"
        interp = f"{ticker} candidate score is below {leader}. This points to possible sector/theme-led movement rather than individual leadership."
    else:
        setup = "in_line_with_leader"
        interp = f"{ticker} is moving in line with {leader}. This points to broad theme participation."

    return {
        "leader": leader,
        "leader_score": leader_score,
        "relative_setup": setup,
        "interpretation": interp
    }

def determine_move_scope(candidate, sector_compare, relationship_map):
    ticker = candidate.get("ticker")
    rel = relationship_map.get(ticker, {})
    relative_setup = sector_compare.get("relative_setup")

    if relative_setup == "outperforming_leader":
        move_scope = "company_specific_leadership"
    elif relative_setup == "lagging_leader":
        move_scope = "sector_or_theme_led"
    elif relative_setup == "in_line_with_leader":
        move_scope = "broad_theme_participation"
    else:
        move_scope = "undetermined"

    return move_scope

def determine_competitor_effect(candidate, candidate_lookup, relationship_map):
    ticker = candidate.get("ticker")
    rel = relationship_map.get(ticker, {})
    competitors = rel.get("competitors", [])
    inverse_competitors = rel.get("inverse_competitors", [])

    effects = []

    ticker_score = safe_float(candidate.get("candidate_score"))

    for peer in competitors:
        peer_obj = candidate_lookup.get(peer)

        if peer_obj:
            peer_score = safe_float(peer_obj.get("candidate_score"))
            if peer in inverse_competitors:
                if ticker_score > peer_score:
                    effect = "negative_share_take_pressure"
                    note = f"{ticker} strength may pressure {peer} if market reads the event as share capture."
                else:
                    effect = "inverse_peer_leading"
                    note = f"{peer} is stronger than {ticker}; market may be favoring the competitor."
            else:
                if ticker_score > 0 and peer_score > 0:
                    effect = "positive_sympathy"
                    note = f"{ticker} and {peer} are both positive, suggesting the event may benefit the group."
                elif ticker_score > 0 and peer_score <= 0:
                    effect = "isolated_or_share_shift"
                    note = f"{ticker} is positive while {peer} is not, suggesting possible company-specific leadership or share shift."
                else:
                    effect = "unclear"
                    note = f"Peer relationship between {ticker} and {peer} is unclear."

            effects.append({
                "peer": peer,
                "peer_score": peer_score,
                "relationship": "inverse" if peer in inverse_competitors else "same_theme",
                "effect": effect,
                "note": note
            })
        else:
            effects.append({
                "peer": peer,
                "relationship": "inverse" if peer in inverse_competitors else "same_theme",
                "effect": "peer_not_in_current_scan",
                "note": f"{peer} is mapped as related but is not in the current candidate packet."
            })

    return effects

def enrich_relationships(candidate_packet):
    if not isinstance(candidate_packet, dict):
        return candidate_packet

    candidates = candidate_packet.get("top_candidates", [])
    relationship_map = ensure_map()
    candidate_lookup = {c.get("ticker"): c for c in candidates if isinstance(c, dict)}

    for c in candidates:
        ticker = c.get("ticker")
        rel = relationship_map.get(ticker, {})

        sector_compare = compare_to_sector_leader(c, candidate_lookup, relationship_map)
        move_scope = determine_move_scope(c, sector_compare, relationship_map)
        competitor_effects = determine_competitor_effect(c, candidate_lookup, relationship_map)

        c["sector_leader_comparison"] = sector_compare
        c["sector_competitor_effects"] = competitor_effects
        c["relationship_context"] = {
            "move_scope_determined": move_scope,
            "primary_theme": rel.get("primary_theme", "unknown"),
            "move_logic": rel.get("move_logic", "unknown"),
            "theme_chain": rel.get("theme_chain", []),
            "theme_chain_summary": " → ".join(rel.get("theme_chain", [])) if rel.get("theme_chain") else "No chain mapped",
            "upstream": rel.get("upstream", []),
            "downstream": rel.get("downstream", []),
            "adjacent": rel.get("adjacent", []),
            "competitors": rel.get("competitors", []),
            "inverse_competitors": rel.get("inverse_competitors", []),
            "economic_transmission": rel.get("economic_transmission", "No transmission logic mapped yet.")
        }
        c["theme_phase"] = infer_theme_phase(c)

    candidate_packet["relationship_enriched_at"] = utc_now()
    return candidate_packet
