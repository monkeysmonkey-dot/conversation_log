import csv
import json
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse

BASE = Path(__file__).resolve().parents[1]

IN_CSV = BASE / "data" / "thesis_sources.csv"
REVIEW_JSON = BASE / "data" / "thesis_source_review.json"
THESIS_DB = BASE / "data" / "thesis_database.json"

OUT_JSON = BASE / "features" / "latest_thesis_source_review.json"
OUT_MD = BASE / "reports" / "daily" / "latest_thesis_source_review.md"


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
        return urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        return ""


def classify_source(url, source_platform, source_type):
    blob = " ".join([url, source_platform, source_type]).lower()
    domain = domain_of(url)

    official_domains = [
        "sec.gov",
        "sedarplus.ca",
        "sedar.com",
        "sedi.ca",
        "usaspending.gov",
        "canada.ca",
        "gc.ca",
        "federalregister.gov",
        "company",
        "investor",
        "ir."
    ]

    video_social_domains = [
        "youtube.com",
        "youtu.be",
        "x.com",
        "twitter.com",
        "reddit.com",
        "tiktok.com"
    ]

    news_research_terms = [
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
        "cnbc"
    ]

    if any(d in domain for d in official_domains) or any(x in blob for x in ["official filing", "sec", "sedar", "government", "company filing", "annual report", "quarterly report"]):
        return {
            "source_category": "official_or_primary_source",
            "source_trust": "trusted_after_user_confirmation",
            "verification_required": False,
            "evidence_status": "usable_after_confirmation",
            "verification_note": "Primary or official source. User confirmation still required before promotion."
        }

    if any(d in domain for d in video_social_domains):
        return {
            "source_category": "video_social_or_commentary",
            "source_trust": "unverified",
            "verification_required": True,
            "evidence_status": "research_lead_pending_verification",
            "verification_note": "Video/social source should be treated as a thesis lead only until claims are verified from primary sources."
        }

    if any(x in blob for x in news_research_terms):
        return {
            "source_category": "third_party_research_or_article",
            "source_trust": "unverified",
            "verification_required": True,
            "evidence_status": "research_lead_pending_verification",
            "verification_note": "Third-party article/research should be independently verified before being used as evidence."
        }

    return {
        "source_category": "unknown_or_manual_source",
        "source_trust": "unverified_until_reviewed",
        "verification_required": True,
        "evidence_status": "pending_user_review",
        "verification_note": "Source category unclear. User review and independent verification required."
    }


def infer_tags(row):
    url = clean(row.get("url"))
    title = clean(row.get("title"))
    blob = " ".join([
        url,
        title,
        clean(row.get("theme")),
        clean(row.get("sector")),
        clean(row.get("ecosystem_layer")),
        clean(row.get("why_saved")),
        clean(row.get("claimed_fact"))
    ]).lower()

    tags = []

    if "ai" in blob:
        tags.append("AI")
    if "power" in blob or "grid" in blob or "electric" in blob:
        tags.append("Power/Grid")
    if "nuclear" in blob or "uranium" in blob:
        tags.append("Nuclear/Uranium")
    if "semiconductor" in blob or "chip" in blob or "gpu" in blob or "hbm" in blob:
        tags.append("Semiconductors")
    if "data center" in blob or "datacenter" in blob:
        tags.append("Data Centers")
    if "contract" in blob or "award" in blob or "mou" in blob:
        tags.append("Deal/Contract")
    if "capex" in blob or "capital expenditure" in blob:
        tags.append("Capex")
    if "earnings" in blob or "revenue" in blob:
        tags.append("Earnings")

    return sorted(set(tags))


def build_review_item(row, idx):
    url = clean(row.get("url"))
    source = classify_source(url, row.get("source_platform"), row.get("source_type"))
    verified_raw = clean(row.get("verified")).lower()
    user_marked_verified = verified_raw in ["true", "yes", "1", "verified"]

    review_status = "confirmed" if user_marked_verified and not source["verification_required"] else "pending_user_confirmation"

    item = {
        "source_id": f"source_{idx}",
        "date_added": clean(row.get("date_added")) or now_utc(),
        "url": url,
        "domain": domain_of(url),
        "title": clean(row.get("title")),
        "source_platform": clean(row.get("source_platform")),
        "source_type": clean(row.get("source_type")),
        "ticker": clean(row.get("ticker")).upper(),
        "theme": clean(row.get("theme")),
        "sector": clean(row.get("sector")),
        "ecosystem_layer": clean(row.get("ecosystem_layer")),
        "thesis_tag": clean(row.get("thesis_tag")),
        "auto_tags": infer_tags(row),
        "why_saved": clean(row.get("why_saved")),
        "claimed_fact": clean(row.get("claimed_fact")),
        "user_notes": clean(row.get("user_notes")),
        "source_category": source["source_category"],
        "source_trust": source["source_trust"],
        "verification_required": source["verification_required"],
        "evidence_status": source["evidence_status"],
        "verification_note": source["verification_note"],
        "user_marked_verified": user_marked_verified,
        "review_status": review_status,
        "next_action": "Confirm/edit source classification and verify claims if required.",
        "advisory_only": True,
        "updated_at": now_utc()
    }

    return item


def update_thesis_database(review_items):
    db = load_json(THESIS_DB, {"sources": [], "theses": []})
    existing = {item.get("url"): item for item in db.get("sources", [])}

    promoted = 0
    pending = 0

    for item in review_items:
        if not item.get("url"):
            continue

        db_item = {
            **item,
            "usable_as_evidence": item.get("review_status") == "confirmed" and not item.get("verification_required"),
            "database_status": "evidence" if item.get("review_status") == "confirmed" and not item.get("verification_required") else "lead_pending_verification",
            "added_to_database_at": now_utc()
        }

        if db_item["usable_as_evidence"]:
            promoted += 1
        else:
            pending += 1

        existing[item["url"]] = db_item

    db["sources"] = sorted(existing.values(), key=lambda x: (x.get("theme", ""), x.get("ticker", ""), x.get("title", "")))
    db["updated_at"] = now_utc()
    db["policy"] = {
        "official_or_primary_source": "Can become evidence after user confirmation.",
        "video_social_or_commentary": "Research lead only until claims are verified from primary/official sources.",
        "third_party_research_or_article": "Research lead only until independently verified.",
        "advisory_only": True
    }

    save_json(THESIS_DB, db)

    return promoted, pending, len(db["sources"])


def main():
    rows = read_csv(IN_CSV)
    review_items = []

    for idx, row in enumerate(rows, start=1):
        if not any(clean(v) for v in row.values()):
            continue
        review_items.append(build_review_item(row, idx))

    promoted, pending, total = update_thesis_database(review_items)

    payload = {
        "timestamp": now_utc(),
        "sources_reviewed": len(review_items),
        "verified_or_primary_promoted": promoted,
        "pending_verification": pending,
        "database_total_sources": total,
        "review_items": review_items,
        "advisory_only": True
    }

    save_json(REVIEW_JSON, payload)
    save_json(OUT_JSON, payload)

    lines = []
    lines.append("# Thesis Source Review")
    lines.append("")
    lines.append(f"Created: {payload['timestamp']}")
    lines.append(f"- Sources reviewed: {payload['sources_reviewed']}")
    lines.append(f"- Promoted as evidence/source: {payload['verified_or_primary_promoted']}")
    lines.append(f"- Pending verification: {payload['pending_verification']}")
    lines.append(f"- Thesis database total sources: {payload['database_total_sources']}")
    lines.append("")
    lines.append("## Sources")

    for item in review_items[:100]:
        lines.append("")
        lines.append(f"### {item.get('title') or item.get('url')}")
        lines.append(f"- URL: {item.get('url')}")
        lines.append(f"- Ticker: {item.get('ticker')}")
        lines.append(f"- Theme: {item.get('theme')}")
        lines.append(f"- Ecosystem layer: {item.get('ecosystem_layer')}")
        lines.append(f"- Source category: {item.get('source_category')}")
        lines.append(f"- Verification required: {item.get('verification_required')}")
        lines.append(f"- Evidence status: {item.get('evidence_status')}")
        lines.append(f"- Claimed fact: {item.get('claimed_fact')}")
        lines.append(f"- Next action: {item.get('next_action')}")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "sources_reviewed": payload["sources_reviewed"],
        "promoted": promoted,
        "pending_verification": pending,
        "database_total_sources": total,
        "json": str(OUT_JSON)
    }, indent=2))


if __name__ == "__main__":
    main()
