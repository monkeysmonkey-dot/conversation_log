import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]
MANIFEST = BASE / "data" / "document_inbox" / "manifest.json"
OUT = BASE / "features" / "latest_document_intake.json"

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

def classify(name):
    n = name.lower()

    if any(x in n for x in ["portfolio", "holding", "position", "balance"]):
        return ("Portfolio Update / Holdings File", "Account Portfolio / Tax", "Stock Account", "Review")
    if any(x in n for x in ["contribution", "payroll", "match"]):
        return ("Contribution / Payroll Match", "Mutual Fund / Retirement", "Company Retirement", "Company Retirement")
    if any(x in n for x in ["t5008", "tax", "trading", "gain", "loss"]):
        return ("Tax / Trading Summary", "Tax Advisor", "Stock Account", "Cash / Non-registered")
    if "tfsa" in n:
        return ("TFSA Statement", "Account Portfolio / Tax", "Stock Account", "TFSA")
    if "rrsp" in n or "rsp" in n:
        return ("RRSP Statement", "Account Portfolio / Tax", "Stock Account", "RRSP")
    if "fhsa" in n:
        return ("FHSA Statement", "Account Portfolio / Tax", "Stock Account", "FHSA")
    if any(x in n for x in ["fund", "factsheet", "mer", "retirement", "pension"]):
        return ("Mutual Fund Factsheet", "Mutual Fund / Retirement", "Company Retirement", "Company Retirement")
    if any(x in n for x in ["earnings", "transcript", "research", "article", "analyst", "sedar", "10-k", "10-q"]):
        return ("Research Article / News", "Market Research / Thesis", "Research", "Research")
    if any(x in n for x in ["fx", "usd", "cad", "exchange"]):
        return ("FX / Currency Record", "FX / Currency Tracking", "Currency", "FX")

    return ("Other / Review", "Needs Confirmation", "Unknown", "Unknown")

def main():
    packet = load(MANIFEST, {"documents": []})
    docs = packet.get("documents", [])

    for doc in docs:
        doc.setdefault("status", "pending_confirmation")
        doc_type, destination, group, acct = classify(doc.get("filename", ""))

        doc["suggestion"] = {
            "document_type": doc_type,
            "destination": destination,
            "account_group": group,
            "account_type": acct,
            "tax_relevance": "Review",
            "confidence": "filename based",
            "reason": "Initial filename-based sorting. User confirmation required."
        }

    packet["documents"] = docs
    packet["updated_at"] = now()
    save(MANIFEST, packet)

    out = {
        "timestamp": now(),
        "total_documents": len(docs),
        "pending_confirmation": len([d for d in docs if d.get("status") != "confirmed"]),
        "confirmed": len([d for d in docs if d.get("status") == "confirmed"]),
        "documents": docs
    }

    save(OUT, out)

    print(json.dumps({
        "status": "complete",
        "total_documents": out["total_documents"],
        "pending_confirmation": out["pending_confirmation"],
        "confirmed": out["confirmed"]
    }, indent=2))

if __name__ == "__main__":
    main()
