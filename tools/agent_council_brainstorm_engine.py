import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]

CHAT_LOG = BASE / "data" / "agent_chat_idea_lab.jsonl"
OUT_JSON = BASE / "features" / "latest_agent_council_brainstorm.json"
OUT_MD = BASE / "reports" / "daily" / "latest_agent_council_brainstorm.md"


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


def agent_response(agent, thought, category):
    blob = str(thought or "").lower()

    if agent == "Intake / Memory Agent":
        return {
            "read": "Captured as a brainstorm item and preserved for later review.",
            "concern": "Needs category, route, and next action kept clear.",
            "suggested_next": "Keep in Idea Lab and link to the proper workflow."
        }

    if agent == "Market Thesis Agent":
        if any(x in blob for x in ["stock", "ticker", "earnings", "price", "sector", "thesis", "catalyst"]):
            return {
                "read": "This may be market/thesis-relevant.",
                "concern": "Do not treat the idea as evidence until verified against source data.",
                "suggested_next": "Send to Agent Reports / thesis research for verification."
            }
        return {
            "read": "No direct market thesis signal detected.",
            "concern": "Market impact may be indirect.",
            "suggested_next": "Only route to market research if a ticker/sector/catalyst is added."
        }

    if agent == "Portfolio / Risk Agent":
        if any(x in blob for x in ["position", "account", "allocation", "risk", "exposure", "rebalance"]):
            return {
                "read": "This may affect portfolio allocation or risk exposure.",
                "concern": "Need account type, currency, and position size before acting.",
                "suggested_next": "Review in Account Portfolio / Tax and portfolio risk context."
            }
        return {
            "read": "No immediate portfolio risk action detected.",
            "concern": "Could become relevant if linked to a holding or account.",
            "suggested_next": "Keep as advisory note."
        }

    if agent == "Tax Advisor Agent":
        if any(x in blob for x in ["tax", "loss", "gain", "tfsa", "rrsp", "fhsa", "cash", "cad", "usd"]):
            return {
                "read": "This may have Canadian tax/account implications.",
                "concern": "Taxable vs registered account treatment must stay separated.",
                "suggested_next": "Review in Tax Advisor before any trade or reallocation."
            }
        return {
            "read": "No direct tax trigger detected.",
            "concern": "Tax impact may still appear if this later affects taxable accounts.",
            "suggested_next": "No tax action yet."
        }

    if agent == "Mutual Fund / Retirement Agent":
        if any(x in blob for x in ["mutual fund", "retirement", "fund", "mer", "pension", "allocation", "cash option"]):
            return {
                "read": "This belongs in the retirement/mutual fund analysis workflow.",
                "concern": "Need fund list, cash yield, MER, performance, and holdings where available.",
                "suggested_next": "Send to Mutual Fund / Retirement for allocation review."
            }
        return {
            "read": "No retirement fund signal detected.",
            "concern": "May still matter if it affects company retirement allocation.",
            "suggested_next": "Keep outside retirement workflow unless fund/account context is added."
        }

    if agent == "Research Verification Agent":
        return {
            "read": "Treat this as an idea, not verified fact.",
            "concern": "Uploaded research/news/manual notes must be independently verified unless personal/source/official documents.",
            "suggested_next": "Require verification before using as thesis, tax, or portfolio evidence."
        }

    if agent == "System Architect Agent":
        if any(x in blob for x in ["build", "button", "dashboard", "agent", "workflow", "automation", "patch", "feature", "ui", "system"]):
            return {
                "read": "This likely implies a Hermes system or workflow improvement.",
                "concern": "Need to avoid clutter and preserve advisory-only controls.",
                "suggested_next": "Create a Build Ideas Queue item."
            }
        return {
            "read": "No system-build requirement detected.",
            "concern": "Could become a build idea if repeated or operationally useful.",
            "suggested_next": "Archive as brainstorm unless user flags as task."
        }

    if agent == "Implementation Planner Agent":
        if category == "System Implementation" or any(x in blob for x in ["build", "patch", "code", "dashboard", "button", "workflow"]):
            return {
                "read": "This can be converted into an implementation candidate.",
                "concern": "Needs clear scope, affected files, expected UI behavior, and rollback safety.",
                "suggested_next": "Draft a patch plan before coding."
            }
        return {
            "read": "No immediate implementation plan needed.",
            "concern": "Keep this available for future build planning.",
            "suggested_next": "No patch until user confirms."
        }

    return {
        "read": "No response.",
        "concern": "",
        "suggested_next": ""
    }


def main():
    rows = read_jsonl(CHAT_LOG)

    latest = rows[-1] if rows else None

    if not latest:
        payload = {
            "timestamp": now_utc(),
            "status": "no_ideas",
            "headline": "No brainstorm ideas available yet.",
            "agent_responses": [],
            "implementation_flag": False
        }
    else:
        thought = latest.get("user_thought", "")
        category = latest.get("category", "General Thought")

        agents = [
            "Intake / Memory Agent",
            "Market Thesis Agent",
            "Portfolio / Risk Agent",
            "Tax Advisor Agent",
            "Mutual Fund / Retirement Agent",
            "Research Verification Agent",
            "System Architect Agent",
            "Implementation Planner Agent",
        ]

        responses = []

        for agent in agents:
            r = agent_response(agent, thought, category)
            responses.append({
                "agent": agent,
                "read": r.get("read"),
                "concern": r.get("concern"),
                "suggested_next": r.get("suggested_next")
            })

        implementation_flag = any(
            x in str(thought).lower()
            for x in ["build", "button", "dashboard", "agent", "workflow", "automation", "patch", "feature", "ui", "system"]
        ) or category == "System Implementation"

        payload = {
            "timestamp": now_utc(),
            "status": "complete",
            "headline": "Agent Council reviewed latest brainstorm idea.",
            "latest_thought": thought,
            "category": category,
            "route": latest.get("route", ""),
            "implementation_flag": implementation_flag,
            "agent_responses": responses,
            "recommended_summary": {
                "decision": "Hold as brainstorm until user confirms next step.",
                "if_market_related": "Verify sources before thesis use.",
                "if_tax_related": "Review in Tax Advisor before action.",
                "if_system_related": "Convert to Build Ideas Queue only after user approval."
            }
        }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = []
    lines.append("# Agent Council Brainstorm")
    lines.append("")
    lines.append(f"Created: {payload['timestamp']}")
    lines.append("")
    lines.append(f"## {payload['headline']}")
    lines.append("")
    if payload.get("latest_thought"):
        lines.append(f"Thought: {payload.get('latest_thought')}")
        lines.append("")
    lines.append("## Agent Responses")
    for item in payload.get("agent_responses", []):
        lines.append("")
        lines.append(f"### {item.get('agent')}")
        lines.append(f"- Read: {item.get('read')}")
        lines.append(f"- Concern: {item.get('concern')}")
        lines.append(f"- Next: {item.get('suggested_next')}")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": payload.get("status"),
        "implementation_flag": payload.get("implementation_flag", False),
        "json": str(OUT_JSON)
    }, indent=2))


if __name__ == "__main__":
    main()
