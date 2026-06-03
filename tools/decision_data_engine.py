import json
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter

BASE = Path(__file__).resolve().parents[1]

MANUAL_ACTIONS = BASE / "data" / "manual_actions_journal.jsonl"
AGENT_SUGGESTIONS = BASE / "data" / "agent_suggestions_journal.jsonl"
THESIS_HEALTH = BASE / "data" / "thesis_health_journal.jsonl"
PORTFOLIO_SNAPSHOT = BASE / "data" / "portfolio_snapshot.json"

OUT_JSON = BASE / "features" / "latest_decision_data_status.json"
OUT_MD = BASE / "reports" / "daily" / "latest_decision_data_status.md"


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def ensure_file(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("", encoding="utf-8")


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


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def latest_by_ticker(rows):
    out = {}
    for row in rows:
        ticker = row.get("ticker")
        if ticker:
            out[ticker] = row
    return out


def status_badge(condition):
    return "ready" if condition else "missing"


def main():
    ensure_file(MANUAL_ACTIONS)
    ensure_file(AGENT_SUGGESTIONS)
    ensure_file(THESIS_HEALTH)

    manual = read_jsonl(MANUAL_ACTIONS)
    suggestions = read_jsonl(AGENT_SUGGESTIONS)
    thesis = read_jsonl(THESIS_HEALTH)
    portfolio = load_json(PORTFOLIO_SNAPSHOT, {})

    manual_by_type = Counter([x.get("action_type", "unknown") for x in manual])
    suggestion_by_type = Counter([x.get("suggestion_type", "unknown") for x in suggestions])
    thesis_by_status = Counter([x.get("thesis_status", "unknown") for x in thesis])

    latest_manual = latest_by_ticker(manual)
    latest_suggestion = latest_by_ticker(suggestions)
    latest_thesis = latest_by_ticker(thesis)

    readiness = {
        "manual_actions_journal": status_badge(len(manual) > 0),
        "agent_suggestions_journal": status_badge(len(suggestions) > 0),
        "thesis_health_journal": status_badge(len(thesis) > 0),
        "portfolio_snapshot": status_badge(bool(portfolio)),
        "actual_pnl_ready": status_badge(len(manual) > 0 and bool(portfolio)),
        "agent_replay_ready": status_badge(len(suggestions) > 0),
        "thesis_health_ready": status_badge(len(thesis) > 0),
    }

    missing = [
        name for name, status in readiness.items()
        if status != "ready"
    ]

    if len(missing) == 0:
        overall = "ready"
        read = "Decision data layer is ready for P&L, suggestion replay, and thesis health analysis."
    else:
        overall = "data_missing"
        read = "Decision data layer is not ready yet. Missing data prevents reliable P&L or replay analysis."

    payload = {
        "timestamp": now_utc(),
        "overall_status": overall,
        "read": read,
        "readiness": readiness,
        "missing": missing,
        "counts": {
            "manual_actions": len(manual),
            "agent_suggestions": len(suggestions),
            "thesis_records": len(thesis),
            "portfolio_snapshot_present": bool(portfolio),
        },
        "manual_action_types": dict(manual_by_type),
        "agent_suggestion_types": dict(suggestion_by_type),
        "thesis_status_counts": dict(thesis_by_status),
        "latest_manual_by_ticker": latest_manual,
        "latest_suggestion_by_ticker": latest_suggestion,
        "latest_thesis_by_ticker": latest_thesis,
        "files": {
            "manual_actions": str(MANUAL_ACTIONS),
            "agent_suggestions": str(AGENT_SUGGESTIONS),
            "thesis_health": str(THESIS_HEALTH),
            "portfolio_snapshot": str(PORTFOLIO_SNAPSHOT),
        }
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = []
    lines.append("# Decision Data Status")
    lines.append("")
    lines.append(f"Created: {payload['timestamp']}")
    lines.append("")
    lines.append(f"- Overall status: {overall}")
    lines.append(f"- Read: {read}")
    lines.append("")
    lines.append("## Counts")
    for k, v in payload["counts"].items():
        lines.append(f"- {k}: {v}")

    lines.append("")
    lines.append("## Missing")
    if missing:
        for item in missing:
            lines.append(f"- {item}")
    else:
        lines.append("- None")

    lines.append("")
    lines.append("## Readiness")
    for k, v in readiness.items():
        lines.append(f"- {k}: {v}")

    lines.append("")
    lines.append("## Files")
    for k, v in payload["files"].items():
        lines.append(f"- {k}: {v}")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "overall_status": overall,
        "json": str(OUT_JSON),
        "report": str(OUT_MD),
        "missing_count": len(missing)
    }, indent=2))


if __name__ == "__main__":
    main()
