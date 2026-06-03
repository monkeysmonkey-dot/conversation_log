import csv
import json
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse

BASE = Path(__file__).resolve().parents[1]

INBOX = BASE / "data" / "source_link_inbox.csv"
REVIEW_JSON = BASE / "data" / "source_link_sorting_review.json"
RESEARCH_DB = BASE / "data" / "research_database.json"
THESIS_DB = BASE / "data" / "thesis_database.json"

OUT_JSON = BASE / "features" / "latest_source_link_sorting_review.json"
OUT_MD = BASE / "reports" / "daily" / "latest_source_link_sorting_review.md"


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def clean(value):
    return str(value or "").strip()


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def read_csv(path):
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as f:
        return list(csv.DictReader(f))


def domain_of(url):
    try:
        return urlparse(clean(url)).netloc.lower().replace("www.", "")
    except Exception:
        return ""


def classify_link(url, note):
    domain = domain_of(url)
    blob = f"{url} {note} {domain}".lower()

    official_domains = [
        "sec.gov",
        "sedarplus.ca",
        "sedar.com",
        "sedi.ca",
        "usaspending.gov",
        "canada.ca",
        "gc.ca",
        "federalregister.gov",
        "open.fec.gov",
        "api.open.fec.gov"
    ]

    official_terms = [
        "10-k",
        "10-q",
        "8-k",
        "6-k",
        "20-f",
        "annual report",
        "quarterly report",
        "official filing",
        "company filing",
        "government contract",
        "contract award",
        "procurement",
        "issuer document",
        "investor relations",
        "press release"
    ]

    video_social_domains = [
        "youtube.com",
        "youtu.be",
        "x.com",
        "twitter.com",
        "reddit.com",
        "tiktok.com"
    ]

    article_terms = [
        "article",
        "news",
        "blog",
        "newsletter",
        "research",
        "substack",
        "seekingalpha",
        "marketwatch",
        "bloomberg",
        "reuters",
        "cnbc",
        "yahoo",
        "morningstar"
    ]

    if any(d in domain for d in official_domains) or any(x in blob for x in official_terms):
        return {
            "source_category": "official_or_primary_source",
            "source_type": "official / primary source",
            "source_trust": "trusted_after_user_confirmation",
            "verification_required": False,
            "evidence_status": "usable_after_confirmation",
            "route": "research_database",
            "reason": "Link appears to be an official, regulator, government, company, issuer, or primary-source document."
        }

    if any(d in domain for d in video_social_domains):
        return {
            "source_category": "video_social_or_commentary",
            "source_type": "video / social commentary",
            "source_trust": "unverified",
            "verification_required": True,
            "evidence_status": "research_lead_pending_verification",
            "route": "thesis_database_lead",
            "reason": "Video/social link should be treated as a thesis lead until claims are verified from primary sources."
        }

    if any(x in blob for x in article_terms):
        return {
            "source_category": "third_party_article_or_research",
            "source_type": "article / third-party research",
            "source_trust": "unverified",
            "verification_required": True,
            "evidence_status": "research_lead_pending_verification",
            "route": "thesis_database_lead",
            "reason": "Third-party article/research should be independently verified before being used as evidence."
        }

    return {
        "source_category": "unknown_link_source",
        "source_type": "unknown link",
        "source_trust": "unverified_until_reviewed",
        "verification_required": True,
        "evidence_status": "pending_user_review",
        "route": "manual_sorting_review",
        "reason": "Sorting agent could not confidently classify this source."
    }


def infer_theme_tags(url, note):
    blob = f"{url} {note}".lower()
    tags = []

    if "ai" in blob or "artificial intelligence" in blob:
        tags.append("AI")
    if "grid" in blob or "power" in blob or "electric" in blob or "utility" in blob:
        tags.append("Power/Grid")
    if "uranium" in blob or "nuclear" in blob or "smr" in blob:
        tags.append("Nuclear/Uranium")
    if "semiconductor" in blob or "chip" in blob or "gpu" in blob or "hbm" in blob:
        tags.append("Semiconductors")
    if "data center" in blob or "datacenter" in blob:
        tags.append("Data Centers")
    if "contract" in blob or "award" in blob or "mou" in blob or "deal" in blob:
        tags.append("Deal/Contract")
    if "capex" in blob or "capital expenditure" in blob:
        tags.append("Capex")
    if "filing" in blob or "10-k" in blob or "10-q" in blob or "8-k" in blob:
        tags.append("Filing")

    return sorted(set(tags))


def infer_destination(classification):
    if classification.get("verification_required"):
        return "Thesis / Research Lead Review"
    return "Research Database"


def make_fact_sheet(row, idx):
    url = clean(row.get("url"))
    note = clean(row.get("user_note"))
    status = clean(row.get("status")) or "pending_user_confirmation"

    classification = classify_link(url, note)

    fact_sheet = {
        "source_id": f"link_source_{idx}",
        "date_added": clean(row.get("date_added")) or now_utc(),
        "url": url,
        "domain": domain_of(url),
        "user_note": note,
        "review_status": status,
        "agent_prefill": {
            "source_type": classification.get("source_type"),
            "source_category": classification.get("source_category"),
            "destination": infer_destination(classification),
            "route": classification.get("route"),
            "auto_tags": infer_theme_tags(url, note)
        },
        "editable_fields": {
            "source_type": classification.get("source_type"),
            "source_category": classification.get("source_category"),
            "theme": "",
            "ticker": "",
            "sector": "",
            "ecosystem_layer": "",
            "claimed_fact": "",
            "user_notes": note,
            "verification_required": classification.get("verification_required")
        },
        "source_trust": classification.get("source_trust"),
        "verification_required": classification.get("verification_required"),
        "evidence_status": classification.get("evidence_status"),
        "sorting_reason": classification.get("reason"),
        "next_action": "User confirms or edits source fact sheet. If non-official, verify claims before evidence use.",
        "advisory_only": True,
        "updated_at": now_utc()
    }

    return fact_sheet


def update_databases(fact_sheets):
    research = load_json(RESEARCH_DB, {"documents": [], "sources": []})
    thesis = load_json(THESIS_DB, {"sources": [], "theses": []})

    research_sources = {x.get("url"): x for x in research.get("sources", [])}
    thesis_sources = {x.get("url"): x for x in thesis.get("sources", [])}

    research_added = 0
    thesis_added = 0

    for fs in fact_sheets:
        if not fs.get("url"):
            continue

        entry = {
            "source_id": fs.get("source_id"),
            "url": fs.get("url"),
            "domain": fs.get("domain"),
            "source_type": fs.get("editable_fields", {}).get("source_type"),
            "source_category": fs.get("editable_fields", {}).get("source_category"),
            "theme": fs.get("editable_fields", {}).get("theme", ""),
            "ticker": fs.get("editable_fields", {}).get("ticker", ""),
            "sector": fs.get("editable_fields", {}).get("sector", ""),
            "ecosystem_layer": fs.get("editable_fields", {}).get("ecosystem_layer", ""),
            "claimed_fact": fs.get("editable_fields", {}).get("claimed_fact", ""),
            "verification_required": fs.get("verification_required"),
            "evidence_status": fs.get("evidence_status"),
            "usable_as_evidence": fs.get("review_status") == "confirmed" and not fs.get("verification_required"),
            "database_status": "evidence" if fs.get("review_status") == "confirmed" and not fs.get("verification_required") else "lead_pending_verification",
            "user_note": fs.get("user_note"),
            "added_at": now_utc(),
            "advisory_only": True
        }

        if entry["usable_as_evidence"]:
            research_sources[entry["url"]] = entry
            research_added += 1
        else:
            thesis_sources[entry["url"]] = entry
            thesis_added += 1

    research["sources"] = sorted(research_sources.values(), key=lambda x: x.get("url", ""))
    research["updated_at"] = now_utc()
    research["policy"] = {
        "official_primary_sources": "Evidence after user confirmation.",
        "third_party_video_article_sources": "Research lead until independently verified.",
        "advisory_only": True
    }

    thesis["sources"] = sorted(thesis_sources.values(), key=lambda x: x.get("url", ""))
    thesis["updated_at"] = now_utc()
    thesis["policy"] = {
        "purpose": "Stores thesis leads, links, and unverified source claims for follow-up verification.",
        "non_official_sources": "Do not treat as evidence until verified.",
        "advisory_only": True
    }

    save_json(RESEARCH_DB, research)
    save_json(THESIS_DB, thesis)

    return research_added, thesis_added, len(research["sources"]), len(thesis["sources"])


def main():
    rows = read_csv(INBOX)
    fact_sheets = []

    for idx, row in enumerate(rows, start=1):
        if not clean(row.get("url")):
            continue
        fact_sheets.append(make_fact_sheet(row, idx))

    research_added, thesis_added, research_total, thesis_total = update_databases(fact_sheets)

    payload = {
        "timestamp": now_utc(),
        "links_reviewed": len(fact_sheets),
        "pending_user_confirmation": len([x for x in fact_sheets if x.get("review_status") != "confirmed"]),
        "verification_required": len([x for x in fact_sheets if x.get("verification_required")]),
        "research_added": research_added,
        "thesis_leads_added": thesis_added,
        "research_total_sources": research_total,
        "thesis_total_sources": thesis_total,
        "fact_sheets": fact_sheets,
        "advisory_only": True
    }

    save_json(REVIEW_JSON, payload)
    save_json(OUT_JSON, payload)

    lines = []
    lines.append("# Source Link Sorting Review")
    lines.append("")
    lines.append(f"Created: {payload['timestamp']}")
    lines.append(f"- Links reviewed: {payload['links_reviewed']}")
    lines.append(f"- Pending user confirmation: {payload['pending_user_confirmation']}")
    lines.append(f"- Verification required: {payload['verification_required']}")
    lines.append(f"- Research evidence/source added: {payload['research_added']}")
    lines.append(f"- Thesis leads added: {payload['thesis_leads_added']}")
    lines.append("")
    lines.append("## Fact Sheets")

    for fs in fact_sheets[:100]:
        lines.append("")
        lines.append(f"### {fs.get('url')}")
        lines.append(f"- Domain: {fs.get('domain')}")
        lines.append(f"- Agent source type: {fs.get('agent_prefill', {}).get('source_type')}")
        lines.append(f"- Destination: {fs.get('agent_prefill', {}).get('destination')}")
        lines.append(f"- Verification required: {fs.get('verification_required')}")
        lines.append(f"- Evidence status: {fs.get('evidence_status')}")
        lines.append(f"- Auto tags: {', '.join(fs.get('agent_prefill', {}).get('auto_tags', []))}")
        lines.append(f"- Reason: {fs.get('sorting_reason')}")
        lines.append(f"- Next action: {fs.get('next_action')}")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "links_reviewed": payload["links_reviewed"],
        "pending_user_confirmation": payload["pending_user_confirmation"],
        "verification_required": payload["verification_required"],
        "thesis_leads_added": payload["thesis_leads_added"],
        "research_added": payload["research_added"],
        "json": str(OUT_JSON)
    }, indent=2))


if __name__ == "__main__":
    main()
