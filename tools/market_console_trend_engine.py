import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]

DECISION_BRIEF_PATH = BASE / "features" / "latest_decision_explanations.json"
MARKET_MECH_PATH = BASE / "features" / "latest_market_mechanics.json"
QUAL_QUEUE_PATH = BASE / "features" / "latest_qualitative_research_queue.json"
PERFORMANCE_PATH = BASE / "features" / "latest_platform_performance.json"

HISTORY_PATH = BASE / "data" / "market_console_trend_history.jsonl"
OUT_JSON = BASE / "features" / "latest_market_console_trends.json"
OUT_MD = BASE / "reports" / "daily" / "latest_market_console_trends.md"


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def append_jsonl(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path):
    if not path.exists():
        return []

    rows = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            if line.strip():
                rows.append(json.loads(line))
        except Exception:
            pass
    return rows


def simple_trend(metric, values):
    clean = [x for x in values if x not in [None, "", "unknown"]]

    if len(clean) < 2:
        return "No trend history yet."

    last = clean[-1]
    prev = clean[-2]

    if isinstance(last, (int, float)) and isinstance(prev, (int, float)):
        if last > prev:
            return f"{metric} rising."
        if last < prev:
            return f"{metric} falling."
        return f"{metric} stable."

    if str(last) == str(prev):
        return f"{metric} stable at {last}."

    return f"{metric} changed from {prev} to {last}."


def main():
    decision = load_json(DECISION_BRIEF_PATH, {})
    macro = decision.get("macro_explanation", {})

    market_mech = load_json(MARKET_MECH_PATH, {})
    qual_queue = load_json(QUAL_QUEUE_PATH, {})
    perf = load_json(PERFORMANCE_PATH, {})

    mechanical_pressure = market_mech.get("summary", {}).get("mechanical_pressure", "unknown")
    qual_count = qual_queue.get("task_count", len(qual_queue.get("created", [])))
    macro_confidence = macro.get("confidence", "unknown")
    roi_score = perf.get("platform_roi_score", "data_missing")

    snapshot = {
        "timestamp": now_utc(),
        "macro_confidence": macro_confidence,
        "mechanical_pressure": mechanical_pressure,
        "qual_tasks": qual_count,
        "platform_roi": roi_score,
        "health_status": "tracked"
    }

    append_jsonl(HISTORY_PATH, snapshot)
    history = read_jsonl(HISTORY_PATH)

    def values_for(key):
        return [row.get(key) for row in history]

    payload = {
        "timestamp": now_utc(),
        "history_count": len(history),
        "latest_snapshot": snapshot,
        "trends": {
            "macro_confidence": {
                "trend_read": simple_trend("Macro confidence", values_for("macro_confidence"))
            },
            "mechanical_pressure": {
                "trend_read": simple_trend("Mechanical pressure", values_for("mechanical_pressure"))
            },
            "qual_tasks": {
                "trend_read": simple_trend("Qualitative task count", values_for("qual_tasks"))
            },
            "platform_roi": {
                "trend_read": simple_trend("Platform ROI", values_for("platform_roi"))
            },
            "bull_momentum": {
                "trend_read": "Bull momentum trend is derived from macro positives, mechanics, and confirmation quality."
            },
            "bear_risk": {
                "trend_read": "Bear risk trend is derived from negative impacts, mechanical pressure, and unresolved qualitative work."
            },
            "health_status": {
                "trend_read": "Health status tracks whether expected files and engines exist."
            }
        },
        "report_path": str(OUT_MD),
        "history_path": str(HISTORY_PATH)
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = []
    lines.append("# Market Console Trends")
    lines.append("")
    lines.append(f"Created: {payload['timestamp']}")
    lines.append(f"History count: {payload['history_count']}")
    lines.append("")
    lines.append("## Latest Snapshot")
    lines.append(f"- Macro confidence: {macro_confidence}")
    lines.append(f"- Mechanical pressure: {mechanical_pressure}")
    lines.append(f"- Qualitative tasks: {qual_count}")
    lines.append(f"- Platform ROI: {roi_score}")
    lines.append("")
    lines.append("## Trend Reads")
    for key, value in payload["trends"].items():
        lines.append(f"- {key}: {value.get('trend_read')}")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "history_count": payload["history_count"],
        "json": str(OUT_JSON),
        "report": str(OUT_MD)
    }, indent=2))


if __name__ == "__main__":
    main()
