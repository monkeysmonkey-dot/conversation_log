import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]

MANIFEST = BASE / "data" / "document_inbox" / "manifest.json"

OUT_JSON = BASE / "features" / "latest_document_sorting_review.json"
OUT_MD = BASE / "reports" / "daily" / "latest_document_sorting_review.md"

REVIEW_DB = BASE / "data" / "document_sorting_review.json"
RESEARCH_DB = BASE / "data" / "research_database.json"


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def clean(value):
    return str(value or "").strip()


def lower_blob(*values):
    return " ".join([clean(v).lower() for v in values])


def classify_source(filename, suggestion=None, confirmed=None):
    suggestion = suggestion or {}
    confirmed = confirmed or {}

    blob = lower_blob(
        filename,
        suggestion.get("document_type"),
        suggestion.get("destination"),
        suggestion.get("source_type"),
        confirmed.get("document_type"),
        confirmed.get("destination"),
        confirmed.get("source_type"),
    )

    official_terms = [
        "sec",
        "sedar",
        "sedi",
        "edgar",
        "10-k",
        "10-q",
        "8-k",
        "6-k",
        "20-f",
        "annual report",
        "quarterly report",
        "company filing",
        "regulatory filing",
        "government",
        "official",
        "contract award",
        "usaspending",
        "issuer",
        "company source",
        "company presentation",
        "factsheet",
        "fund facts",
        "mutual fund facts",
    ]

    personal_terms = [
        "portfolio",
        "holding",
        "holdings",
        "broker",
        "brokerage",
        "statement",
        "account balance",
        "contribution",
        "payroll",
        "tax slip",
        "t5008",
        "t3",
        "t5",
        "rrsp",
        "tfsa",
        "fhsa",
        "resp",
        "retirement",
    ]

    unverified_terms = [
        "article",
        "news",
        "blog",
        "research note",
        "manual note",
        "screenshot",
        "opinion",
        "tweet",
        "social",
        "analyst note",
        "third party",
    ]

    if any(term in blob for term in personal_terms):
        return {
            "source_category": "personal_or_portfolio_source",
            "source_trust": "trusted_after_user_confirmation",
            "verification_required": False,
            "evidence_status": "usable_after_confirmation",
            "reason": "Document appears to be portfolio/account/personal-source related."
        }

    if any(term in blob for term in official_terms):
        return {
            "source_category": "official_or_primary_source",
            "source_trust": "trusted_after_user_confirmation",
            "verification_required": False,
            "evidence_status": "usable_after_confirmation",
            "reason": "Document appears to be an official, issuer, regulator, government, or primary-source document."
        }

    if any(term in blob for term in unverified_terms):
        return {
            "source_category": "third_party_or_manual_research",
            "source_trust": "unverified",
            "verification_required": True,
            "evidence_status": "research_lead_pending_verification",
            "reason": "Document appears to be news/research/manual/third-party content and must be independently verified."
        }

    return {
        "source_category": "unknown_source",
        "source_trust": "unverified_until_reviewed",
        "verification_required": True,
        "evidence_status": "pending_user_review",
        "reason": "Source type could not be confidently identified."
    }


def infer_designation(filename):
    blob = clean(filename).lower()

    if any(x in blob for x in ["portfolio", "holding", "holdings", "position"]):
        return {
            "document_type": "Portfolio Update / Holdings File",
            "destination": "Portfolio Database",
            "route": "portfolio_csv_import_engine.py"
        }

    if any(x in blob for x in ["account balance", "statement", "brokerage"]):
        return {
            "document_type": "Account Balance / Broker Statement",
            "destination": "Portfolio Database",
            "route": "portfolio_csv_import_engine.py"
        }

    if any(x in blob for x in ["tax", "t5008", "t3", "t5", "rrsp", "tfsa", "fhsa", "resp"]):
        return {
            "document_type": "Tax / Account Document",
            "destination": "Tax Advisor",
            "route": "tax_advisor_engine.py"
        }

    if any(x in blob for x in ["fund", "factsheet", "fund facts", "mutual"]):
        return {
            "document_type": "Mutual Fund / Retirement Factsheet",
            "destination": "Mutual Fund Review",
            "route": "mutual_fund_analysis_engine.py"
        }

    if any(x in blob for x in ["10-k", "10-q", "8-k", "annual", "quarterly", "sec", "sedar", "filing"]):
        return {
            "document_type": "Company Filing / Official Disclosure",
            "destination": "Research Database",
            "route": "research_database"
        }

    if any(x in blob for x in ["contract", "mou", "deal", "award", "grant", "procurement"]):
        return {
            "document_type": "Policy / Deal / Contract Evidence",
            "destination": "Policy Deal Flow Database",
            "route": "policy_deal_flow_engine.py"
        }

    if any(x in blob for x in ["article", "news", "research", "note"]):
        return {
            "document_type": "Research / News Lead",
            "destination": "Research Database",
            "route": "research_database"
        }

    return {
        "document_type": "Unsorted Document",
        "destination": "Document Inbox Review",
        "route": "manual_review"
    }


def make_fact_sheet(doc):
    filename = clean(doc.get("filename"))
    suggestion = doc.get("suggestion", {}) or {}
    confirmed = doc.get("confirmed_designation", {}) or {}

    inferred = infer_designation(filename)
    source = classify_source(filename, suggestion=suggestion, confirmed=confirmed)

    user_confirmed = bool(confirmed)

    designation = {
        "document_type": confirmed.get("document_type") or suggestion.get("document_type") or inferred.get("document_type"),
        "destination": confirmed.get("destination") or suggestion.get("destination") or inferred.get("destination"),
        "route": confirmed.get("route") or suggestion.get("route") or inferred.get("route"),
    }

    if user_confirmed:
        review_status = "confirmed"
    else:
        review_status = "pending_user_confirmation"

    fact_sheet = {
        "document_id": filename,
        "filename": filename,
        "path": doc.get("path"),
        "uploaded_at": doc.get("uploaded_at"),
        "review_status": review_status,
        "designation": designation,
        "source_category": source.get("source_category"),
        "source_trust": source.get("source_trust"),
        "verification_required": source.get("verification_required"),
        "evidence_status": source.get("evidence_status"),
        "source_reason": source.get("reason"),
        "agent_prefill": {
            "document_type": inferred.get("document_type"),
            "destination": inferred.get("destination"),
            "route": inferred.get("route")
        },
        "user_confirmed_designation": confirmed,
        "editable_fields": {
            "document_type": designation.get("document_type"),
            "destination": designation.get("destination"),
            "route": designation.get("route"),
            "source_category": source.get("source_category"),
            "verification_required": source.get("verification_required"),
            "notes": doc.get("notes", "")
        },
        "next_action": determine_next_action(user_confirmed, source, designation),
        "advisory_only": True,
        "updated_at": now_utc()
    }

    return fact_sheet


def determine_next_action(user_confirmed, source, designation):
    if not user_confirmed:
        return "User review required. Confirm or edit the fact sheet/designation."

    if source.get("verification_required"):
        return "Confirmed as document type, but facts require independent verification before use as evidence."

    destination = clean(designation.get("destination")).lower()

    if "portfolio" in destination:
        return "Confirmed portfolio/account document. Route to portfolio import/account update workflow."

    if "research" in destination:
        return "Confirmed source document. Add to research database."

    if "tax" in destination:
        return "Confirmed tax/account document. Route to tax advisor workflow."

    return "Confirmed. Store in document database and route to assigned workflow."


def update_research_database(fact_sheets):
    db = load_json(RESEARCH_DB, {"documents": []})
    docs = db.get("documents", [])

    by_id = {item.get("document_id"): item for item in docs}

    promoted = 0
    pending_verification = 0

    for fs in fact_sheets:
        if fs.get("review_status") != "confirmed":
            continue

        destination = clean(fs.get("designation", {}).get("destination")).lower()

        if "research" not in destination and "policy" not in destination and "deal" not in destination:
            continue

        entry = {
            "document_id": fs.get("document_id"),
            "filename": fs.get("filename"),
            "path": fs.get("path"),
            "document_type": fs.get("designation", {}).get("document_type"),
            "destination": fs.get("designation", {}).get("destination"),
            "source_category": fs.get("source_category"),
            "source_trust": fs.get("source_trust"),
            "verification_required": fs.get("verification_required"),
            "evidence_status": fs.get("evidence_status"),
            "usable_as_evidence": not bool(fs.get("verification_required")),
            "added_at": now_utc(),
            "advisory_only": True
        }

        if entry["usable_as_evidence"]:
            promoted += 1
        else:
            pending_verification += 1

        by_id[entry["document_id"]] = entry

    db["documents"] = sorted(by_id.values(), key=lambda x: clean(x.get("filename")))
    db["updated_at"] = now_utc()
    db["policy"] = {
        "official_or_primary_source": "Can be used as evidence after user confirmation.",
        "personal_or_portfolio_source": "Can be used for portfolio/account/tax workflows after user confirmation.",
        "third_party_or_manual_research": "Stored as research lead only until independently verified.",
        "advisory_only": True
    }

    save_json(RESEARCH_DB, db)

    return promoted, pending_verification, len(db["documents"])


def main():
    manifest = load_json(MANIFEST, {"documents": []})
    documents = manifest.get("documents", [])

    fact_sheets = [make_fact_sheet(doc) for doc in documents]

    review_payload = {
        "timestamp": now_utc(),
        "fact_sheets": fact_sheets,
        "pending_user_confirmation": len([x for x in fact_sheets if x.get("review_status") != "confirmed"]),
        "confirmed": len([x for x in fact_sheets if x.get("review_status") == "confirmed"]),
        "verification_required": len([x for x in fact_sheets if x.get("verification_required")]),
        "advisory_only": True
    }

    save_json(REVIEW_DB, review_payload)
    save_json(OUT_JSON, review_payload)

    promoted, pending_verification, research_total = update_research_database(fact_sheets)

    lines = []
    lines.append("# Document Sorting Review")
    lines.append("")
    lines.append(f"Created: {review_payload['timestamp']}")
    lines.append(f"- Documents reviewed: {len(fact_sheets)}")
    lines.append(f"- Pending user confirmation: {review_payload['pending_user_confirmation']}")
    lines.append(f"- Confirmed: {review_payload['confirmed']}")
    lines.append(f"- Verification required: {review_payload['verification_required']}")
    lines.append(f"- Research DB promoted as evidence/source: {promoted}")
    lines.append(f"- Research DB pending verification: {pending_verification}")
    lines.append(f"- Research DB total: {research_total}")
    lines.append("")
    lines.append("## Fact Sheets")

    for fs in fact_sheets[:80]:
        lines.append("")
        lines.append(f"### {fs.get('filename')}")
        lines.append(f"- Status: {fs.get('review_status')}")
        lines.append(f"- Type: {fs.get('designation', {}).get('document_type')}")
        lines.append(f"- Destination: {fs.get('designation', {}).get('destination')}")
        lines.append(f"- Source category: {fs.get('source_category')}")
        lines.append(f"- Verification required: {fs.get('verification_required')}")
        lines.append(f"- Evidence status: {fs.get('evidence_status')}")
        lines.append(f"- Next action: {fs.get('next_action')}")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "documents": len(fact_sheets),
        "pending_user_confirmation": review_payload["pending_user_confirmation"],
        "confirmed": review_payload["confirmed"],
        "verification_required": review_payload["verification_required"],
        "research_db_total": research_total,
        "json": str(OUT_JSON)
    }, indent=2))


if __name__ == "__main__":
    main()
