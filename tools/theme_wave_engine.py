import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]
CANDIDATES = BASE / "features" / "latest_candidates.json"
REL_MAP = BASE / "config" / "prospect_relationship_map.json"
OUT_JSON = BASE / "features" / "latest_theme_wave_analysis.json"
OUT_MD = BASE / "reports" / "weekly" / "latest_theme_wave_analysis.md"

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

def phase_from_candidate(c):
    conviction = safe_float(c.get("conviction_rate"))
    trend = safe_float(c.get("trend_score"))
    rs = safe_float(c.get("relative_strength_vs_spy"))
    vol = safe_float(c.get("volume_ratio"))
    sentiment = str(c.get("qualitative_sentiment", "")).lower()
    macro = str(c.get("macro_alignment", "")).lower()

    if trend >= 10 and rs > 0 and vol < 1 and sentiment in ["missing", ""]:
        return {
            "phase": "early_or_unconfirmed_momentum",
            "consensus": "not_confirmed",
            "bubble_risk": "low_to_medium",
            "fomo_risk": "medium",
            "smart_investing_read": "watch_for_confirmation",
            "profit_take_read": "not_applicable_for_new_entry",
            "interpretation": "Strong price leadership exists, but volume and narrative confirmation are incomplete."
        }

    if trend >= 10 and vol >= 1.2 and conviction >= 75:
        return {
            "phase": "momentum_expansion",
            "consensus": "rising",
            "bubble_risk": "medium",
            "fomo_risk": "medium_to_high",
            "smart_investing_read": "participate_only_with_risk_control",
            "profit_take_read": "trim_if_volume_fades_or_rank_drops",
            "interpretation": "Trend, participation, and conviction are aligned. Watch for crowding and late-cycle chase behavior."
        }

    if conviction >= 85 and sentiment == "positive":
        return {
            "phase": "consensus_build",
            "consensus": "rising",
            "bubble_risk": "medium",
            "fomo_risk": "medium",
            "smart_investing_read": "constructive_if_not_extended",
            "profit_take_read": "take_partial_profit_if_price_accelerates_without_new_data",
            "interpretation": "Strong score and positive narrative suggest consensus may be forming."
        }

    if trend < 5:
        return {
            "phase": "lagging_or_base_building",
            "consensus": "weak",
            "bubble_risk": "low",
            "fomo_risk": "low",
            "smart_investing_read": "wait_for_breakout_or_catalyst",
            "profit_take_read": "not_applicable",
            "interpretation": "The prospect is not leading yet. It may be a lagger or base-building candidate."
        }

    return {
        "phase": "watchlist_confirmation_needed",
        "consensus": "unclear",
        "bubble_risk": "unknown",
        "fomo_risk": "medium",
        "smart_investing_read": "wait_for_confirmation",
        "profit_take_read": "not_applicable",
        "interpretation": "The setup needs more evidence from volume, catalyst, sentiment, filings, or peer confirmation."
    }

def determine_spread_type(c, rel):
    theme = rel.get("primary_theme", "unknown")
    competitors = rel.get("competitors", [])
    inverse = rel.get("inverse_competitors", [])
    upstream = rel.get("upstream", [])
    downstream = rel.get("downstream", [])
    adjacent = rel.get("adjacent", [])

    if inverse:
        peer_effect = "may_create_inverse_competitor_pressure"
    elif upstream or downstream or adjacent:
        peer_effect = "may_spread_through_theme_chain"
    else:
        peer_effect = "relationship_not_mapped"

    return {
        "primary_theme": theme,
        "peer_effect": peer_effect,
        "competitors": competitors,
        "inverse_competitors": inverse,
        "upstream": upstream,
        "downstream": downstream,
        "adjacent": adjacent
    }

def analyze_theme_waves():
    packet = load_json(CANDIDATES, {})
    rel_map = load_json(REL_MAP, {})
    candidates = packet.get("top_candidates", [])

    analysis = {
        "timestamp": utc_now(),
        "theme_wave_items": [],
        "top_next_beneficiaries": [],
        "risk_flags": [],
        "summary": []
    }

    beneficiary_scores = {}

    for c in candidates:
        ticker = c.get("ticker")
        rel = rel_map.get(ticker, {})
        phase = phase_from_candidate(c)
        spread = determine_spread_type(c, rel)

        item = {
            "ticker": ticker,
            "candidate_score": c.get("candidate_score"),
            "conviction_rate": c.get("conviction_rate"),
            "phase": phase,
            "spread": spread,
            "theme_chain": rel.get("theme_chain", []),
            "economic_transmission": rel.get("economic_transmission", ""),
            "risk_chain": rel.get("risk_chain", []),
            "interpretation": phase.get("interpretation")
        }

        analysis["theme_wave_items"].append(item)

        for name in spread.get("upstream", []) + spread.get("downstream", []) + spread.get("adjacent", []):
            beneficiary_scores[name] = beneficiary_scores.get(name, 0) + safe_float(c.get("conviction_rate"))

        for risk in rel.get("risk_chain", []):
            if risk not in analysis["risk_flags"]:
                analysis["risk_flags"].append(risk)

    ranked_beneficiaries = sorted(
        [{"name": k, "theme_score": round(v, 1)} for k, v in beneficiary_scores.items()],
        key=lambda x: x["theme_score"],
        reverse=True
    )

    analysis["top_next_beneficiaries"] = ranked_beneficiaries[:25]

    # Summary bullets.
    for item in analysis["theme_wave_items"][:10]:
        analysis["summary"].append(
            f"{item['ticker']}: {item['phase']['phase']} / {item['spread']['peer_effect']} / theme {item['spread']['primary_theme']}"
        )

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# Theme Wave Analysis")
    lines.append("")
    lines.append(f"Created: {analysis['timestamp']}")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    for s in analysis["summary"]:
        lines.append(f"- {s}")

    lines.append("")
    lines.append("## Top Next Beneficiaries / Relationship Prospects")
    lines.append("")
    for b in analysis["top_next_beneficiaries"]:
        lines.append(f"- {b['name']}: relationship score {b['theme_score']}")

    lines.append("")
    lines.append("## Theme Wave Items")
    lines.append("")
    for item in analysis["theme_wave_items"]:
        lines.append(f"### {item['ticker']}")
        lines.append("")
        lines.append(f"- Candidate score: {item['candidate_score']}")
        lines.append(f"- Conviction rate: {item['conviction_rate']}%")
        lines.append(f"- Phase: {item['phase']['phase']}")
        lines.append(f"- Consensus: {item['phase']['consensus']}")
        lines.append(f"- Bubble risk: {item['phase']['bubble_risk']}")
        lines.append(f"- FOMO risk: {item['phase']['fomo_risk']}")
        lines.append(f"- Smart investing read: {item['phase']['smart_investing_read']}")
        lines.append(f"- Profit-taking read: {item['phase']['profit_take_read']}")
        lines.append(f"- Peer spread type: {item['spread']['peer_effect']}")
        lines.append(f"- Theme chain: {' → '.join(item['theme_chain']) if item['theme_chain'] else 'No chain mapped'}")
        lines.append(f"- Economic transmission: {item['economic_transmission']}")
        lines.append("")
        lines.append("Risks:")
        for r in item["risk_chain"]:
            lines.append(f"- {r}")
        lines.append("")

    lines.append("## Risk Flags Across Themes")
    lines.append("")
    for r in analysis["risk_flags"]:
        lines.append(f"- {r}")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    return analysis

if __name__ == "__main__":
    result = analyze_theme_waves()
    print(json.dumps({
        "status": "complete",
        "json": str(OUT_JSON),
        "report": str(OUT_MD),
        "theme_items": len(result["theme_wave_items"])
    }, indent=2))
