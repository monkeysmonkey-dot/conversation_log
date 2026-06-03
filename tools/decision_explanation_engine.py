import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]

CANDIDATES = BASE / "features" / "latest_candidates.json"
MACRO_MASTER = BASE / "features" / "latest_macro_master_analysis.json"
MARKET_MECHANICS = BASE / "features" / "latest_market_mechanics.json"
QUAL_QUEUE = BASE / "features" / "latest_qualitative_research_queue.json"
ASSOCIATION = BASE / "features" / "latest_association_intelligence.json"

OUT_JSON = BASE / "features" / "latest_decision_explanations.json"
OUT_MD = BASE / "reports" / "daily" / "latest_decision_explanations.md"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def pct(x):
    try:
        return f"{float(x) * 100:.1f}%"
    except Exception:
        return "unknown"


def safe_round(x, n=3):
    try:
        return round(float(x), n)
    except Exception:
        return x


def first_nonempty(*vals):
    for v in vals:
        if v not in [None, "", [], {}, "unknown"]:
            return v
    return "unknown"


def extract_reason(candidate):
    reason = candidate.get("reason")
    if isinstance(reason, str) and reason.strip():
        return reason.strip()

    reasons = candidate.get("reasons", [])
    if isinstance(reasons, list) and reasons:
        return ", ".join([str(x) for x in reasons[:5]])

    return "No clear reason parsed yet."


def infer_main_blocker(candidate):
    blockers = []

    vol = candidate.get("volume_ratio")
    try:
        if float(vol) < 1.0:
            blockers.append("volume confirmation is thin")
    except Exception:
        pass

    if candidate.get("qualitative_sentiment", "missing") in ["missing", None, ""]:
        blockers.append("qualitative sentiment is missing")

    filing_signal = candidate.get("filing_signal") or candidate.get("whale_filing_signal")
    if not filing_signal or filing_signal in ["none", "unknown"]:
        blockers.append("no confirmed whale / insider / filing signal")

    fq = candidate.get("financial_quality", {})
    val = fq.get("valuation_profile") or fq.get("valuation")
    if isinstance(val, str) and "expensive" in val:
        blockers.append("valuation requires execution confirmation")

    if not blockers:
        blockers.append("confirmation still needs volume, narrative, or peer validation")

    return "; ".join(blockers[:4])


def infer_flow_read(candidate):
    flow = candidate.get("flow_interpretation", {})
    if isinstance(flow, dict):
        interp = flow.get("interpretation")
        if interp:
            return interp

    vol_ramp = candidate.get("volume_ramp", "unknown")
    vol_ratio = candidate.get("volume_ratio", "unknown")

    return f"Flow is not fully confirmed. Volume ramp is {vol_ramp}, volume ratio is {vol_ratio}."


def infer_affected_companies(candidate):
    names = []

    rel = candidate.get("relationship_theme_chain", {}) or candidate.get("relationship_chain", {})
    for key in ["upstream_beneficiaries", "downstream_beneficiaries", "adjacent_names", "competitors", "possible_upstream_beneficiaries", "possible_downstream_beneficiaries"]:
        vals = rel.get(key, [])
        if isinstance(vals, list):
            names.extend(vals)

    market = candidate.get("market_structure", {})
    for key in ["direct_competitors", "indirect_competitors", "who_shares_the_market"]:
        vals = market.get(key, [])
        if isinstance(vals, list):
            names.extend(vals)
        elif isinstance(vals, str):
            names.extend([x.strip() for x in vals.split(",") if x.strip()])

    cleaned = []
    for x in names:
        x = str(x).strip()
        if x and x not in cleaned:
            cleaned.append(x)

    return cleaned[:12]


def build_ticker_explanation(candidate, market_mechanics):
    ticker = candidate.get("ticker", "UNKNOWN")
    conviction = candidate.get("conviction_rate")
    candidate_score = candidate.get("candidate_score")
    trend_score = candidate.get("trend_score")
    rs = candidate.get("relative_strength_vs_spy")
    macro = candidate.get("macro_alignment", candidate.get("macro", "unknown"))
    reason = extract_reason(candidate)
    blocker = infer_main_blocker(candidate)
    flow_read = infer_flow_read(candidate)

    fq = candidate.get("financial_quality", {})
    rel = candidate.get("relationship_theme_chain", {}) or candidate.get("relationship_chain", {})

    theme = first_nonempty(
        rel.get("primary_theme"),
        candidate.get("primary_theme"),
        "unknown"
    )

    phase = first_nonempty(
        candidate.get("theme_wave_phase"),
        rel.get("phase_estimate"),
        "unknown"
    )

    affected = infer_affected_companies(candidate)

    mechanics_summary = market_mechanics.get("summary", {})
    mech_pressure = mechanics_summary.get("mechanical_pressure", "unknown")
    mech_note = mechanics_summary.get("interpretation", "No mechanics interpretation available.")

    what_happened = (
        f"{ticker} is currently ranked as a watchlist/prospect candidate with candidate score "
        f"{safe_round(candidate_score)} and conviction {conviction if conviction is not None else 'unknown'}."
    )

    why_it_happened = (
        f"The main visible driver is: {reason}. "
        f"Trend score is {safe_round(trend_score)}, relative strength vs SPY is {safe_round(rs)}, "
        f"and macro alignment is {macro}."
    )

    primary_cause = "technical leadership and relative strength"
    if "thin" in str(blocker).lower():
        primary_cause += " with incomplete volume confirmation"

    positive_impacts = []
    negative_impacts = []

    if trend_score is not None:
        positive_impacts.append("Trend leadership supports watchlist attention.")

    if macro in ["supportive", "risk_on", "positive"]:
        positive_impacts.append("Macro alignment appears supportive.")

    if affected:
        positive_impacts.append("Related names may confirm or reject whether the move is theme-wide.")

    negative_impacts.append(blocker)

    if mech_pressure in ["high", "medium"]:
        negative_impacts.append("Market mechanics may distort short-term price action.")

    what_this_could_lead_to = (
        f"If volume, peer confirmation, and narrative improve, {ticker} could upgrade from watchlist to higher-conviction review. "
        f"If confirmation stays weak, this remains a watchlist-only setup."
    )

    suggested_action = (
        "Keep on watchlist and wait for confirmation. "
        "Review volume, relative strength, qualitative narrative, peer/theme confirmation, and market mechanics context before upgrading conviction."
    )

    confidence = "medium"
    try:
        if float(conviction) >= 80 and "thin" not in blocker:
            confidence = "medium_high"
    except Exception:
        pass

    return {
        "ticker": ticker,
        "what_happened": what_happened,
        "why_it_happened": why_it_happened,
        "primary_cause": primary_cause,
        "affected_companies_or_assets": affected,
        "positive_impacts": positive_impacts,
        "negative_impacts": negative_impacts,
        "what_this_could_lead_to": what_this_could_lead_to,
        "suggested_advisory_action": suggested_action,
        "confidence": confidence,
        "key_caveats": [
            blocker,
            "Do not treat mechanical/calendar-driven moves as thesis changes until confirmed after the event window.",
            "This is advisory-only and not a trade instruction."
        ],
        "visible_scorecard": {
            "conviction": conviction,
            "candidate_score": candidate_score,
            "trend_score": trend_score,
            "relative_strength_vs_spy": rs,
            "macro_alignment": macro,
            "volume_ratio": candidate.get("volume_ratio"),
            "volume_ramp": candidate.get("volume_ramp"),
            "financial_quality": fq.get("overall_fundamental_read", "unknown"),
            "theme": theme,
            "theme_phase": phase,
            "market_mechanics_pressure": mech_pressure
        },
        "background_evidence_refs": {
            "reason": reason,
            "flow_read": flow_read,
            "market_mechanics_note": mech_note
        }
    }


def build_macro_explanation(macro_master, market_mechanics, qual_queue, association):
    macro_phase = macro_master.get("macro_phase", {})
    macro_corr = macro_master.get("macro_correlation", {})
    macro_interp = macro_corr.get("macro_interpretation", {})
    mechanics_summary = market_mechanics.get("summary", {})
    queue_tasks = qual_queue.get("created", [])
    hits = association.get("hits", [])

    macro_read = first_nonempty(
        macro_phase.get("macro_read"),
        macro_interp.get("macro_read"),
        "unknown"
    )

    phase = macro_phase.get("phase", "unknown")
    bubble = macro_phase.get("bubble_risk", "unknown")
    recession = macro_phase.get("recession_risk", "unknown")
    mech_pressure = mechanics_summary.get("mechanical_pressure", "unknown")

    top_task = queue_tasks[0] if queue_tasks else {}
    top_sources = top_task.get("suggested_sources", [])

    what_happened = (
        f"Current macro read is {macro_read}. Macro phase is {phase}. "
        f"Bubble risk is {bubble}, recession risk is {recession}, and mechanical flow pressure is {mech_pressure}."
    )

    why_it_happened = (
        "The macro read is based on cross-asset behavior, market mechanics calendar context, "
        "and qualitative association signals."
    )

    affected_assets = ["SPY", "QQQ", "IWM", "TLT", "HYG", "LQD", "GLD", "SLV", "USO", "UUP", "BTC-USD"]

    positive = []
    negative = []

    if macro_read in ["risk_on_or_growth_supportive", "risk_on", "supportive"]:
        positive.append("Risk assets may have a supportive macro backdrop.")

    if mech_pressure in ["high", "medium"]:
        negative.append("Mechanical flow windows may distort short-term price action.")

    if qual_queue.get("task_count", 0):
        negative.append("Qualitative follow-up is still required before fully trusting the narrative.")

    if not positive:
        positive.append("No strong positive macro driver confirmed yet.")

    if not negative:
        negative.append("No major negative macro driver confirmed yet.")

    suggested = (
        "Use macro context as a filter, not as a standalone signal. "
        "Prioritize setups with volume confirmation, relative strength, and post-event stability. "
        "Open the highest-priority qualitative source if narrative confirmation is missing."
    )

    return {
        "what_happened": what_happened,
        "why_it_happened": why_it_happened,
        "primary_cause": "cross-asset regime plus mechanical market calendar context",
        "affected_companies_or_assets": affected_assets,
        "positive_impacts": positive,
        "negative_impacts": negative,
        "what_this_could_lead_to": "Macro conditions may support, distort, or invalidate individual prospect signals depending on confirmation after event windows.",
        "suggested_advisory_action": suggested,
        "confidence": "medium",
        "key_caveats": [
            "Macro regime is not a trade signal by itself.",
            "Mechanical flow windows can temporarily distort price behavior.",
            "Qualitative narrative confirmation may still be incomplete."
        ],
        "top_source_to_check": top_sources[0] if top_sources else "none",
        "association_hit_count": len(hits)
    }


def main():
    candidates_packet = load_json(CANDIDATES, {})
    macro_master = load_json(MACRO_MASTER, {})
    market_mechanics = load_json(MARKET_MECHANICS, {})
    qual_queue = load_json(QUAL_QUEUE, {})
    association = load_json(ASSOCIATION, {})

    candidates = candidates_packet.get("top_candidates", [])

    ticker_explanations = []
    for c in candidates:
        ticker_explanations.append(build_ticker_explanation(c, market_mechanics))

    macro_explanation = build_macro_explanation(
        macro_master,
        market_mechanics,
        qual_queue,
        association
    )

    payload = {
        "timestamp": utc_now(),
        "macro_explanation": macro_explanation,
        "ticker_explanations": ticker_explanations,
        "advisory_note": "This file summarizes decision intelligence only. Raw evidence remains in background files. This is not a trade instruction."
    }

    save_json(OUT_JSON, payload)

    lines = []
    lines.append("# Decision Explanation Brief")
    lines.append("")
    lines.append(f"Created: {payload['timestamp']}")
    lines.append("")
    lines.append("## Macro Brief")
    lines.append("")
    lines.append(f"### What happened")
    lines.append(macro_explanation["what_happened"])
    lines.append("")
    lines.append(f"### Why it happened")
    lines.append(macro_explanation["why_it_happened"])
    lines.append("")
    lines.append(f"### Affected assets")
    lines.append(", ".join(macro_explanation["affected_companies_or_assets"]))
    lines.append("")
    lines.append(f"### Positive impacts")
    for item in macro_explanation["positive_impacts"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append(f"### Negative impacts")
    for item in macro_explanation["negative_impacts"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append(f"### Suggested advisory action")
    lines.append(macro_explanation["suggested_advisory_action"])
    lines.append("")

    lines.append("## Prospect Briefs")
    lines.append("")

    for t in ticker_explanations:
        lines.append(f"### {t['ticker']}")
        lines.append("")
        lines.append(f"**What happened:** {t['what_happened']}")
        lines.append("")
        lines.append(f"**Why it happened:** {t['why_it_happened']}")
        lines.append("")
        lines.append(f"**Primary cause:** {t['primary_cause']}")
        lines.append("")
        lines.append(f"**Affected companies/assets:** {', '.join(t['affected_companies_or_assets']) if t['affected_companies_or_assets'] else 'None mapped'}")
        lines.append("")
        lines.append("**Positive impacts:**")
        for item in t["positive_impacts"]:
            lines.append(f"- {item}")
        lines.append("")
        lines.append("**Negative impacts / blockers:**")
        for item in t["negative_impacts"]:
            lines.append(f"- {item}")
        lines.append("")
        lines.append(f"**What this could lead to:** {t['what_this_could_lead_to']}")
        lines.append("")
        lines.append(f"**Suggested advisory action:** {t['suggested_advisory_action']}")
        lines.append("")
        lines.append(f"**Confidence:** {t['confidence']}")
        lines.append("")

    lines.append("## Advisory Note")
    lines.append(payload["advisory_note"])

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "json": str(OUT_JSON),
        "report": str(OUT_MD),
        "ticker_count": len(ticker_explanations)
    }, indent=2))


if __name__ == "__main__":
    main()
