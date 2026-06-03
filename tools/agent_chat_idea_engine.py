import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]

CHAT_LOG = BASE / "data" / "agent_chat_idea_lab.jsonl"
OUT_JSON = BASE / "features" / "latest_agent_chat_ideas.json"
OUT_MD = BASE / "reports" / "daily" / "latest_agent_chat_ideas.md"


def now_utc():
    return datetime.now(timezone.utc).isoformat()


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


def classify_text(text):
    blob = str(text or "").lower()

    if any(x in blob for x in ["build", "code", "patch", "dashboard", "button", "agent", "workflow", "automation", "implementation", "feature"]):
        return {
            "category": "System Implementation",
            "route": "Build Ideas Queue",
            "priority": "medium",
            "next_action": "Review as possible Hermes system improvement."
        }

    if any(x in blob for x in ["tax", "loss", "gain", "tfsa", "rrsp", "fhsa", "cash account", "capital gain"]):
        return {
            "category": "Tax / Account Planning",
            "route": "Tax Advisor",
            "priority": "medium",
            "next_action": "Review in Tax Advisor before acting."
        }

    if any(x in blob for x in ["mutual fund", "retirement", "mer", "fund", "allocation", "rebalance"]):
        return {
            "category": "Mutual Fund / Retirement",
            "route": "Mutual Fund / Retirement",
            "priority": "medium",
            "next_action": "Review against retirement allocation plan."
        }

    if any(x in blob for x in ["ticker", "stock", "thesis", "entry", "stop", "target", "earnings", "price"]):
        return {
            "category": "Market / Thesis Idea",
            "route": "Agent Reports",
            "priority": "medium",
            "next_action": "Research and verify before using as thesis evidence."
        }

    return {
        "category": "General Thought",
        "route": "Idea Archive",
        "priority": "low",
        "next_action": "Keep as brainstorm note."
    }


def summarize():
    rows = read_jsonl(CHAT_LOG)

    latest = rows[-25:]

    categories = {}
    routes = {}
    implementation_candidates = []

    for row in rows:
        category = row.get("category", "Unknown")
        route = row.get("route", "Unknown")

        categories[category] = categories.get(category, 0) + 1
        routes[route] = routes.get(route, 0) + 1

        if category == "System Implementation":
            implementation_candidates.append(row)

    payload = {
        "timestamp": now_utc(),
        "total_ideas": len(rows),
        "categories": categories,
        "routes": routes,
        "latest": latest,
        "implementation_candidates": implementation_candidates[-20:],
        "source": str(CHAT_LOG)
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = []
    lines.append("# Agent Chat / Idea Lab")
    lines.append("")
    lines.append(f"Created: {payload['timestamp']}")
    lines.append(f"- Total ideas: {payload['total_ideas']}")
    lines.append("")
    lines.append("## Categories")
    for key, value in categories.items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Latest Ideas")
    for item in latest[-10:]:
        lines.append(f"- {item.get('category')}: {item.get('user_thought', '')[:160]}")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "total_ideas": len(rows),
        "implementation_candidates": len(implementation_candidates),
        "json": str(OUT_JSON)
    }, indent=2))


def main():
    summarize()


if __name__ == "__main__":
    main()
