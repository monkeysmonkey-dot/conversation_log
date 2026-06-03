import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]
MANIFEST = BASE / "data" / "document_inbox" / "manifest.json"
OUT = BASE / "features" / "latest_document_router.json"

def now():
    return datetime.now(timezone.utc).isoformat()

def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def route(doc):
    confirmed = doc.get("confirmed_designation", {})
    suggestion = doc.get("suggestion", {})

    doc_type = confirmed.get("document_type") or suggestion.get("document_type", "Other / Review")
    destination = confirmed.get("destination") or suggestion.get("destination", "Needs Confirmation")

    lower = doc_type.lower()

    if "portfolio" in lower or "holding" in lower or "balance" in lower:
        status = "ready_for_portfolio_review"
        action = "Stage for Account Portfolio / Tax review"
    elif "tax" in lower or "trading" in lower:
        status = "ready_for_tax_review"
        action = "Stage for Tax Advisor review"
    elif "fund" in lower or "retirement" in lower:
        status = "ready_for_retirement_review"
        action = "Stage for Mutual Fund / Retirement review"
    elif "research" in lower or "earnings" in lower or "corporate" in lower:
        status = "ready_for_research_review"
        action = "Stage for Agent Reports / thesis research"
    else:
        status = "needs_review"
        action = "Hold for manual confirmation"

    return {
        "file": doc.get("filename", ""),
        "document_type": doc_type,
        "destination": destination,
        "route_status": status,
        "staged_action": action,
        "requires_confirmation": True
    }

def main():
    packet = load(MANIFEST, {"documents": []})
    docs = packet.get("documents", [])

    confirmed = [d for d in docs if d.get("status") == "confirmed"]
    pending = [d for d in docs if d.get("status") != "confirmed"]
    routes = [route(d) for d in confirmed]

    out = {
        "timestamp": now(),
        "confirmed_documents": len(confirmed),
        "pending_documents": len(pending),
        "routes": routes
    }

    save(OUT, out)

    print(json.dumps({
        "status": "complete",
        "confirmed_documents": len(confirmed),
        "pending_documents": len(pending),
        "routes": len(routes)
    }, indent=2))

if __name__ == "__main__":
    main()
