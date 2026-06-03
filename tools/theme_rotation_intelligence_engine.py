import csv
import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]

THEME_REQ = BASE / "data" / "theme_ecosystem_requirements.json"
CAPEX = BASE / "data" / "manual_capex_flow.csv"
DEEP_FLOW = BASE / "features" / "latest_sector_flow_deep_dive.json"
RISK = BASE / "features" / "latest_risk_sentiment.json"

OUT_JSON = BASE / "features" / "latest_theme_rotation_intelligence.json"
OUT_MD = BASE / "reports" / "daily" / "latest_theme_rotation_intelligence.md"


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def safe_float(value):
    try:
        if value in [None, ""]:
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def clamp(value, low=0.0, high=100.0):
    return max(low, min(high, value))


def read_csv(path):
    if not path.exists():
        return []

    try:
        with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def sector_lookup(deep):
    lookup = {}

    for row in deep.get("sector_summary", []):
        sector = row.get("sector")
        if sector:
            lookup[sector] = row

    return lookup


def theme_lookup(deep):
    lookup = {}

    for row in deep.get("theme_summary", []):
        theme = row.get("theme")
        if theme:
            lookup[theme] = row

    return lookup


def capex_by_theme_and_layer(theme_name):
    rows = read_csv(CAPEX)

    matched = []
    by_layer = {}

    for row in rows:
        if str(row.get("theme", "")).strip().lower() != str(theme_name).strip().lower():
            continue

        verified = str(row.get("verified", "")).strip().lower() in ["true", "yes", "1", "verified"]
        amount = safe_float(row.get("amount"))
        layer = row.get("ecosystem_layer", "") or "Unknown"

        item = {
            "date": row.get("date", ""),
            "spender": row.get("spender", ""),
            "receiver": row.get("receiver", ""),
            "receiver_sector": row.get("receiver_sector", ""),
            "ecosystem_layer": layer,
            "region": row.get("region", ""),
            "amount": amount,
            "currency": row.get("amount_currency", ""),
            "capex_type": row.get("capex_type", ""),
            "source": row.get("source", ""),
            "source_type": row.get("source_type", ""),
            "verified": verified,
            "notes": row.get("notes", "")
        }

        matched.append(item)

        by_layer.setdefault(layer, {
            "layer": layer,
            "verified_amount": 0.0,
            "unverified_amount": 0.0,
            "verified_rows": 0,
            "unverified_rows": 0,
            "receivers": set(),
            "spenders": set()
        })

        if verified:
            by_layer[layer]["verified_amount"] += amount
            by_layer[layer]["verified_rows"] += 1
        else:
            by_layer[layer]["unverified_amount"] += amount
            by_layer[layer]["unverified_rows"] += 1

        if row.get("receiver"):
            by_layer[layer]["receivers"].add(row.get("receiver"))
        if row.get("spender"):
            by_layer[layer]["spenders"].add(row.get("spender"))

    finalized = []

    for layer, item in by_layer.items():
        finalized.append({
            "layer": layer,
            "verified_amount": round(item["verified_amount"], 2),
            "unverified_amount": round(item["unverified_amount"], 2),
            "verified_rows": item["verified_rows"],
            "unverified_rows": item["unverified_rows"],
            "receivers": sorted(item["receivers"]),
            "spenders": sorted(item["spenders"])
        })

    return {
        "rows": matched,
        "by_layer": finalized
    }


def layer_money_flow(layer, sector_map):
    matches = layer.get("sector_match", [])
    sector_rows = []

    for sector in matches:
        row = sector_map.get(sector)
        if row:
            sector_rows.append(row)

    if not sector_rows:
        return {
            "money_flow_pct": 0.0,
            "read": "No sector money-flow data",
            "sector_rows": []
        }

    avg = sum(safe_float(x.get("momentum_pct")) for x in sector_rows) / len(sector_rows)

    if avg >= 60:
        read = "Strongly confirming"
    elif avg >= 25:
        read = "Confirming"
    elif avg <= -50:
        read = "Strongly lagging"
    elif avg <= -20:
        read = "Lagging"
    else:
        read = "Mixed / neutral"

    return {
        "money_flow_pct": round(avg, 1),
        "read": read,
        "sector_rows": sector_rows
    }


def capex_confirmation_for_layer(layer_name, capex):
    score = 0
    detail = "No manual capex rows for this layer."

    for item in capex.get("by_layer", []):
        if str(item.get("layer", "")).lower() == str(layer_name).lower():
            verified_rows = item.get("verified_rows", 0)
            unverified_rows = item.get("unverified_rows", 0)
            verified_amount = safe_float(item.get("verified_amount"))

            if verified_rows >= 3:
                score = 100
            elif verified_rows == 2:
                score = 75
            elif verified_rows == 1:
                score = 50
            elif unverified_rows > 0:
                score = 20

            detail = (
                f"Verified rows: {verified_rows}; unverified rows: {unverified_rows}; "
                f"verified amount: {verified_amount}; receivers: {', '.join(item.get('receivers', [])[:5])}"
            )
            break

    return {
        "capex_confirmation_pct": score,
        "capex_detail": detail
    }


def score_theme(theme_def, deep, risk):
    sector_map = sector_lookup(deep)
    themes = theme_lookup(deep)
    capex = capex_by_theme_and_layer(theme_def.get("theme"))

    theme_name = theme_def.get("theme")
    theme_flow = themes.get(theme_name, {})
    money_flow_pct = safe_float(theme_flow.get("momentum_pct"))

    layer_results = []

    total_importance = 0.0
    weighted_completion = 0.0
    weighted_money_flow = 0.0
    weighted_capex = 0.0

    required_lagging = []
    current_winners = []
    next_rotation_candidates = []
    warning_layers = []

    for layer in theme_def.get("required_layers", []):
        importance = safe_float(layer.get("importance", 1))
        completion = safe_float(layer.get("completion_estimate_pct", 0))

        flow = layer_money_flow(layer, sector_map)
        capex_layer = capex_confirmation_for_layer(layer.get("layer"), capex)

        flow_pct = safe_float(flow.get("money_flow_pct"))
        capex_pct = safe_float(capex_layer.get("capex_confirmation_pct"))

        total_importance += importance
        weighted_completion += completion * importance
        weighted_money_flow += flow_pct * importance
        weighted_capex += capex_pct * importance

        status = "balanced"

        if flow_pct >= 50:
            status = "current_winner"
            current_winners.append(layer.get("layer"))

        if completion < 55 and flow_pct < 0:
            status = "lagging_required_layer"
            required_lagging.append(layer.get("layer"))

        if completion < 55 and flow_pct <= 15 and capex_pct >= 20:
            status = "possible_next_rotation"
            next_rotation_candidates.append(layer.get("layer"))

        if completion < 45 and flow_pct <= -30 and capex_pct == 0:
            status = "ecosystem_warning"
            warning_layers.append(layer.get("layer"))

        layer_results.append({
            "layer": layer.get("layer"),
            "sector_match": layer.get("sector_match", []),
            "importance": importance,
            "completion_pct": completion,
            "money_flow_pct": flow_pct,
            "money_flow_read": flow.get("read"),
            "capex_confirmation_pct": capex_pct,
            "capex_detail": capex_layer.get("capex_detail"),
            "status": status,
            "failure_if_missing": layer.get("failure_if_missing"),
            "success_signal": layer.get("success_signal")
        })

    if total_importance <= 0:
        ecosystem_completion = 0
        weighted_flow = 0
        capex_confirmation = 0
    else:
        ecosystem_completion = weighted_completion / total_importance
        weighted_flow = weighted_money_flow / total_importance
        capex_confirmation = weighted_capex / total_importance

    ecosystem_completion = round(clamp(ecosystem_completion), 1)
    weighted_flow = round(max(-100, min(100, weighted_flow)), 1)
    capex_confirmation = round(clamp(capex_confirmation), 1)

    # Innovation reality is not purely price. It needs ecosystem completion + capex + verified traction.
    innovation_reality = clamp(
        (ecosystem_completion * 0.45)
        + (capex_confirmation * 0.30)
        + (max(weighted_flow, 0) * 0.20)
        + (10 if theme_def.get("innovation_type") == "productivity_and_infrastructure_cycle" else 0)
    )

    innovation_reality = round(innovation_reality, 1)

    # Hype risk rises when money flow is strong but completion/capex evidence lags.
    hype_risk = 0.0

    if money_flow_pct >= 60 and ecosystem_completion < 60:
        hype_risk += 25
    if money_flow_pct >= 60 and capex_confirmation < 25:
        hype_risk += 25
    if len(warning_layers) > 0:
        hype_risk += 20
    if len(current_winners) >= 3 and len(required_lagging) >= 2:
        hype_risk += 15
    if risk.get("document_quality", {}).get("unverified_documents", 0) > 0:
        hype_risk += 10

    hype_risk = round(clamp(hype_risk), 1)

    rotation_stage = classify_rotation_stage(
        money_flow_pct=money_flow_pct,
        ecosystem_completion=ecosystem_completion,
        capex_confirmation=capex_confirmation,
        current_winners=current_winners,
        required_lagging=required_lagging,
        next_rotation_candidates=next_rotation_candidates,
        warning_layers=warning_layers
    )

    interpretation = build_interpretation(
        theme_name=theme_name,
        money_flow_pct=money_flow_pct,
        ecosystem_completion=ecosystem_completion,
        innovation_reality=innovation_reality,
        hype_risk=hype_risk,
        current_winners=current_winners,
        required_lagging=required_lagging,
        next_rotation_candidates=next_rotation_candidates,
        warning_layers=warning_layers,
        rotation_stage=rotation_stage
    )

    return {
        "theme": theme_name,
        "status": theme_def.get("status"),
        "global_scope": theme_def.get("global_scope", False),
        "regions": theme_def.get("regions", []),
        "core_question": theme_def.get("core_question"),
        "money_flow_confirmation_pct": round(money_flow_pct, 1),
        "ecosystem_completion_pct": ecosystem_completion,
        "capex_confirmation_pct": capex_confirmation,
        "innovation_reality_pct": innovation_reality,
        "hype_risk_pct": hype_risk,
        "rotation_stage": rotation_stage,
        "current_winners": current_winners,
        "required_lagging_layers": required_lagging,
        "next_rotation_candidates": next_rotation_candidates,
        "warning_layers": warning_layers,
        "layer_results": layer_results,
        "capex_rows": capex.get("rows", []),
        "interpretation": interpretation,
        "advisory_only": True
    }


def classify_rotation_stage(
    money_flow_pct,
    ecosystem_completion,
    capex_confirmation,
    current_winners,
    required_lagging,
    next_rotation_candidates,
    warning_layers
):
    if money_flow_pct < 20 and ecosystem_completion < 40:
        return "Stage 1 — Narrative discovery"

    if money_flow_pct >= 50 and len(current_winners) >= 2 and ecosystem_completion < 65:
        return "Stage 2 — Obvious winners running"

    if len(next_rotation_candidates) > 0:
        return "Stage 3 — Watch bottleneck/required-layer rotation"

    if ecosystem_completion >= 60 and capex_confirmation >= 40:
        return "Stage 4 — Ecosystem buildout confirmation"

    if len(warning_layers) > 0 and capex_confirmation < 25:
        return "Stage 5 — Bottleneck warning / execution risk"

    if money_flow_pct >= 70 and ecosystem_completion < 50:
        return "Stage 6 — Crowding / hype risk"

    return "Mixed — needs more confirmation"


def build_interpretation(
    theme_name,
    money_flow_pct,
    ecosystem_completion,
    innovation_reality,
    hype_risk,
    current_winners,
    required_lagging,
    next_rotation_candidates,
    warning_layers,
    rotation_stage
):
    lines = []

    lines.append(
        f"{theme_name} money-flow confirmation is {money_flow_pct:.1f}%, while ecosystem completion is {ecosystem_completion:.1f}%."
    )

    if current_winners:
        lines.append(
            f"Current winning layers: {', '.join(current_winners[:5])}."
        )

    if required_lagging:
        lines.append(
            f"Required but lagging layers: {', '.join(required_lagging[:5])}."
        )

    if next_rotation_candidates:
        lines.append(
            f"Possible next rotation candidates: {', '.join(next_rotation_candidates[:5])}."
        )

    if warning_layers:
        lines.append(
            f"Warning layers: {', '.join(warning_layers[:5])}. If these do not receive capex or money-flow confirmation, the theme may face scaling constraints."
        )

    if hype_risk >= 60:
        lines.append(
            "Hype risk is elevated because market money is moving faster than ecosystem/capex confirmation."
        )
    elif innovation_reality >= 60 and hype_risk < 50:
        lines.append(
            "Innovation reality is stronger than hype risk, but confirmation should still come from filings, capex, earnings, and verified sources."
        )
    else:
        lines.append(
            "The theme remains mixed and should be monitored for stronger source-verified evidence."
        )

    lines.append(f"Rotation stage: {rotation_stage}.")

    return lines


def main():
    req = load_json(THEME_REQ, {"themes": []})
    deep = load_json(DEEP_FLOW, {})
    risk = load_json(RISK, {})

    themes = []

    for theme_def in req.get("themes", []):
        themes.append(score_theme(theme_def, deep, risk))

    payload = {
        "timestamp": now_utc(),
        "theme_count": len(themes),
        "themes": themes,
        "method": {
            "innovation_reality": "Weighted blend of ecosystem completion, capex confirmation, positive money flow, and innovation type.",
            "ecosystem_completion": "Weighted average of required ecosystem layer completion estimates.",
            "money_flow_confirmation": "Theme momentum from sector/ETF flow engine.",
            "hype_risk": "Rises when market money flow is strong but ecosystem/capex confirmation lags.",
            "advisory_only": True
        }
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = []
    lines.append("# Theme Rotation Intelligence")
    lines.append("")
    lines.append(f"Created: {payload['timestamp']}")
    lines.append("")
    for theme in themes:
        lines.append(f"## {theme['theme']}")
        lines.append(f"- Money Flow Confirmation: {theme['money_flow_confirmation_pct']}%")
        lines.append(f"- Ecosystem Completion: {theme['ecosystem_completion_pct']}%")
        lines.append(f"- Capex Confirmation: {theme['capex_confirmation_pct']}%")
        lines.append(f"- Innovation Reality: {theme['innovation_reality_pct']}%")
        lines.append(f"- Hype Risk: {theme['hype_risk_pct']}%")
        lines.append(f"- Rotation Stage: {theme['rotation_stage']}")
        lines.append("")
        lines.append("### Interpretation")
        for item in theme.get("interpretation", []):
            lines.append(f"- {item}")
        lines.append("")
        lines.append("### Current Winners")
        if theme.get("current_winners"):
            for item in theme.get("current_winners"):
                lines.append(f"- {item}")
        else:
            lines.append("- None detected.")
        lines.append("")
        lines.append("### Required Laggards")
        if theme.get("required_lagging_layers"):
            for item in theme.get("required_lagging_layers"):
                lines.append(f"- {item}")
        else:
            lines.append("- None detected.")
        lines.append("")
        lines.append("### Next Rotation Candidates")
        if theme.get("next_rotation_candidates"):
            for item in theme.get("next_rotation_candidates"):
                lines.append(f"- {item}")
        else:
            lines.append("- None detected.")
        lines.append("")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "themes": len(themes),
        "json": str(OUT_JSON)
    }, indent=2))


if __name__ == "__main__":
    main()
