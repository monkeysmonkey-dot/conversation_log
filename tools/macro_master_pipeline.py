import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]

MACRO_CORR_JSON = BASE / "features" / "latest_macro_correlation_analysis.json"
ASSOC_JSON = BASE / "features" / "latest_association_intelligence.json"
MARKET_MECH_JSON = BASE / "features" / "latest_market_mechanics.json"
BROWSER_CFG = BASE / "config" / "browser_source_config.json"

OUT_JSON = BASE / "features" / "latest_macro_master_analysis.json"
OUT_MD = BASE / "reports" / "macro" / "latest_macro_master_analysis.md"

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default

def run_step(name, cmd, timeout=600):
    try:
        r = subprocess.run(
            cmd,
            cwd=BASE,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        return {
            "name": name,
            "status": "complete" if r.returncode == 0 else "error",
            "returncode": r.returncode,
            "stdout_tail": r.stdout[-2000:],
            "stderr_tail": r.stderr[-2000:]
        }

    except Exception as e:
        return {
            "name": name,
            "status": "failed",
            "error": str(e)
        }


def _task_key(task):
    entities = tuple(sorted(task.get("entities", [])))
    return (
        task.get("task_type"),
        task.get("reason") or task.get("why_it_matters"),
        entities
    )


def build_qualitative_task_queue(macro_data, association_data, browser_cfg):
    macro_interp = macro_data.get("macro_interpretation", {})
    macro_followup_required = macro_interp.get("qualitative_followup_required", False)
    followup_reasons = macro_interp.get("qualitative_followup_reasons", [])

    sources = browser_cfg.get("sources", [])
    allowed_sources = []

    for s in sources:
        allowed_sources.append({
            "id": s.get("id"),
            "label": s.get("label"),
            "url": s.get("url"),
            "source_type": s.get("source_type"),
            "requires_login": s.get("requires_login"),
            "allowed_use": s.get("allowed_use", [])
        })

    tasks = []
    seen = set()

    def add_task(task):
        key = _task_key(task)
        if key in seen:
            return
        seen.add(key)
        tasks.append(task)

    if macro_followup_required:
        for reason in followup_reasons:
            add_task({
                "task_type": "macro_qualitative_followup",
                "reason": reason,
                "priority": "high",
                "suggested_sources": [
                    "perplexity",
                    "investing",
                    "biztoc",
                    "terminal_x"
                ],
                "instruction": "Investigate the narrative or event explanation behind the quantitative macro conflict. View-only research only."
            })

    hits = association_data.get("hits", [])
    for h in hits[:25]:
        entities = h.get("entities", [])

        if len(entities) < 2 and not h.get("patterns"):
            continue

        add_task({
            "task_type": "association_intelligence_followup",
            "association_type": h.get("association_type"),
            "entities": entities,
            "why_it_matters": h.get("why_it_matters"),
            "priority": "medium",
            "suggested_sources": [
                "perplexity",
                "biztoc",
                "terminal_x",
                "hedgefollow_tracker",
                "finviz"
            ],
            "instruction": "Determine why these entities are associated, whether the association is company-specific, sector-wide, theme-wide, policy-driven, or supply-chain related. View-only research only."
        })

    if not tasks:
        add_task({
            "task_type": "routine_macro_qualitative_scan",
            "reason": "No quantitative conflict detected, but routine macro qualitative scan is still useful.",
            "priority": "normal",
            "suggested_sources": [
                "investing",
                "biztoc",
                "perplexity"
            ],
            "instruction": "Check major market headlines, Fed/policy events, CEO interviews, geopolitical risks, and premarket narrative shifts. View-only research only."
        })

    return {
        "macro_quant_followup_required": macro_followup_required,
        "qualitative_tasks_required": len(tasks) > 0,
        "tasks": tasks,
        "approved_sources": allowed_sources,
        "browser_policy": browser_cfg.get("browser_policy", {})
    }


def infer_macro_phase(macro_data):
    interp = macro_data.get("macro_interpretation", {})
    flags = interp.get("flags", [])
    read = interp.get("macro_read", "mixed")

    phase = "mixed_or_unclear"
    bubble_risk = "unknown"
    recession_risk = "unknown"

    if "equities_positive" in flags and "dollar_strength_tightening_pressure" not in flags:
        phase = "risk_on_supportive"
        bubble_risk = "medium_if_breadth_narrows"
        recession_risk = "low_to_medium"
    elif "equities_positive" in flags and "dollar_strength_tightening_pressure" in flags:
        phase = "conflicted_risk_on"
        bubble_risk = "medium"
        recession_risk = "medium"
    elif "bonds_weak_rates_pressure" in flags and "dollar_strength_tightening_pressure" in flags:
        phase = "tightening_pressure"
        bubble_risk = "medium_to_high"
        recession_risk = "medium_to_high"

    if "oil_inflation_pressure" in flags:
        recession_risk = "medium_to_high_if_oil_stays_elevated"

    return {
        "macro_read": read,
        "phase": phase,
        "bubble_risk": bubble_risk,
        "recession_risk": recession_risk,
        "flags": flags
    }

def main():
    steps = []

    steps.append(run_step(
        "macro_correlation_engine",
        ["py", "tools\\macro_correlation_engine.py"],
        timeout=900
    ))

    steps.append(run_step(
        "association_intelligence_engine",
        ["py", "tools\\association_intelligence_engine.py"],
        timeout=600
    ))

    steps.append(run_step(
        "market_mechanics_engine",
        ["py", "tools\\market_mechanics_engine.py"],
        timeout=600
    ))

    macro_data = load_json(MACRO_CORR_JSON, {})
    association_data = load_json(ASSOC_JSON, {})
    market_mechanics_data = load_json(MARKET_MECH_JSON, {})
    browser_cfg = load_json(BROWSER_CFG, {})

    qualitative_queue = build_qualitative_task_queue(
        macro_data,
        association_data,
        browser_cfg
    )

    macro_phase = infer_macro_phase(macro_data)

    payload = {
        "timestamp": utc_now(),
        "steps": steps,
        "macro_phase": macro_phase,
        "macro_correlation": macro_data,
        "association_intelligence": association_data,
        "market_mechanics": market_mechanics_data,
        "qualitative_task_queue": qualitative_queue,
        "view_only_policy": browser_cfg.get("browser_policy", {})
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = []
    lines.append("# 06:00 Macro Master Analysis")
    lines.append("")
    lines.append(f"Created: {payload['timestamp']}")
    lines.append("")
    lines.append("## Macro Phase / Regime Read")
    lines.append("")
    lines.append(f"- Macro read: {macro_phase.get('macro_read')}")
    lines.append(f"- Phase: {macro_phase.get('phase')}")
    lines.append(f"- Bubble risk: {macro_phase.get('bubble_risk')}")
    lines.append(f"- Recession risk: {macro_phase.get('recession_risk')}")
    lines.append("")

    lines.append("## Quantitative Macro Flags")
    lines.append("")
    for flag in macro_phase.get("flags", []):
        lines.append(f"- {flag}")
    if not macro_phase.get("flags"):
        lines.append("- No major quantitative flags detected.")
    lines.append("")

    lines.append("## Market Mechanics / Structural Flow")
    lines.append("")

    mm_summary = market_mechanics_data.get("summary", {})
    lines.append(f"- Mechanical pressure: {mm_summary.get('mechanical_pressure')}")
    lines.append(f"- Interpretation: {mm_summary.get('interpretation')}")
    lines.append("")

    top_mm_events = mm_summary.get("top_events", [])
    if top_mm_events:
        lines.append("### Top Mechanical Events")
        lines.append("")
        for event in top_mm_events[:5]:
            lines.append(f"- {event.get('label')} / {event.get('event_type')} / pressure: {event.get('mechanical_pressure')} / date: {event.get('date')} / read: {event.get('interpretation')}")
    else:
        lines.append("- No configured mechanical events detected.")
    lines.append("")

    lines.append("## Qualitative Follow-Up Queue")
    lines.append("")
    lines.append(f"- Macro quant follow-up required: {qualitative_queue.get('macro_quant_followup_required')}")
    lines.append(f"- Qualitative tasks required: {qualitative_queue.get('qualitative_tasks_required')}")
    lines.append("")
    for task in qualitative_queue.get("tasks", []):
        lines.append(f"### {task.get('task_type')}")
        lines.append(f"- Priority: {task.get('priority')}")
        lines.append(f"- Reason: {task.get('reason') or task.get('why_it_matters')}")
        lines.append(f"- Suggested sources: {', '.join(task.get('suggested_sources', []))}")
        lines.append(f"- Instruction: {task.get('instruction')}")
        if task.get("entities"):
            lines.append(f"- Entities: {', '.join(task.get('entities', []))}")
        lines.append("")

    lines.append("## Association Intelligence Summary")
    lines.append("")
    hits = association_data.get("hits", [])
    if hits:
        for h in hits[:15]:
            lines.append(f"- {h.get('association_type')}: {', '.join(h.get('entities', [])) if h.get('entities') else 'No entities'} — {h.get('why_it_matters')}")
    else:
        lines.append("- No association hits found from currently collected text.")
    lines.append("")

    lines.append("## View-Only Browser Policy")
    lines.append("")
    policy = browser_cfg.get("browser_policy", {})
    lines.append(f"- Mode: {policy.get('mode')}")
    lines.append(f"- Allowed actions: {', '.join(policy.get('allowed_actions', []))}")
    lines.append(f"- Blocked actions: {', '.join(policy.get('blocked_actions', []))}")
    lines.append("")

    lines.append("## Approved Sources")
    lines.append("")
    for src in browser_cfg.get("sources", []):
        lines.append(f"- {src.get('label')}: {src.get('url')} / type: {src.get('source_type')} / login: {src.get('requires_login')}")
    lines.append("")

    lines.append("## Step Status")
    lines.append("")
    for s in steps:
        lines.append(f"- {s.get('name')}: {s.get('status')}")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "json": str(OUT_JSON),
        "report": str(OUT_MD),
        "qualitative_followup_required": qualitative_queue.get("qualitative_tasks_required"),
        "task_count": len(qualitative_queue.get("tasks", []))
    }, indent=2))

if __name__ == "__main__":
    main()
