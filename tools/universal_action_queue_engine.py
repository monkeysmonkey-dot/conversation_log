import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]

SOURCES = {
    "document_sorting": BASE / "data" / "document_sorting_review.json",
    "source_links": BASE / "features" / "latest_source_link_sorting_review.json",
    "portfolio_import": BASE / "features" / "latest_portfolio_csv_import.json",
    "portfolio_reconciliation": BASE / "features" / "latest_portfolio_reconciliation_pipeline.json",
    "watchlist_review": BASE / "features" / "latest_watchlist_review.json",
    "manual_schedule": BASE / "features" / "latest_manual_schedule_status.json",
}

OUT_JSON = BASE / "features" / "latest_universal_action_queue.json"
OUT_MD = BASE / "reports" / "daily" / "latest_universal_action_queue.md"
DB_JSON = BASE / "data" / "universal_action_queue.json"


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def add_item(items, item_type, title, status, priority="normal", source="", details=None, action="Review"):
    items.append({
        "item_id": f"{item_type}_{len(items)+1}",
        "item_type": item_type,
        "title": title,
        "status": status,
        "priority": priority,
        "source": source,
        "action": action,
        "details": details or {},
        "created_at": now_utc(),
        "advisory_only": True
    })


def build_queue():
    items = []

    # Documents / fact sheets
    doc = load_json(SOURCES["document_sorting"], {})
    for fs in doc.get("fact_sheets", []):
        if fs.get("review_status") != "confirmed":
            add_item(
                items,
                "document_confirmation",
                fs.get("filename", "Document needs confirmation"),
                "pending_user_confirmation",
                "high" if fs.get("verification_required") else "normal",
                "document_sorting_review",
                {
                    "destination": fs.get("designation", {}).get("destination"),
                    "verification_required": fs.get("verification_required"),
                    "evidence_status": fs.get("evidence_status"),
                    "source_category": fs.get("source_category")
                },
                "Confirm or edit document fact sheet"
            )

    # Source links
    links = load_json(SOURCES["source_links"], {})
    for fs in links.get("fact_sheets", []):
        if fs.get("review_status") != "confirmed" or fs.get("verification_required"):
            add_item(
                items,
                "source_link_review",
                fs.get("url", "Source link needs review"),
                "verification_required" if fs.get("verification_required") else "pending_user_confirmation",
                "high" if fs.get("verification_required") else "normal",
                "source_link_sorting",
                {
                    "domain": fs.get("domain"),
                    "source_type": fs.get("agent_prefill", {}).get("source_type"),
                    "destination": fs.get("agent_prefill", {}).get("destination"),
                    "evidence_status": fs.get("evidence_status"),
                    "auto_tags": fs.get("agent_prefill", {}).get("auto_tags", [])
                },
                "Confirm source classification / verify claims"
            )

    # Portfolio account sorting
    port = load_json(SOURCES["portfolio_import"], {})
    account_sorting_required = int(port.get("account_sorting_required", 0) or 0)
    if account_sorting_required > 0:
        add_item(
            items,
            "portfolio_account_sorting",
            f"{account_sorting_required} portfolio lots/groups need account sorting",
            "pending_account_sorting",
            "high",
            "portfolio_csv_import",
            {
                "active_lots_imported": port.get("active_lots_imported"),
                "positions_after": port.get("positions_after"),
                "lots_after": port.get("lots_after")
            },
            "Assign Taxable / TFSA / RRSP / FHSA / RESP / Company Retirement"
        )

    # Watchlist candidates
    watch = load_json(SOURCES["watchlist_review"], {})
    pending_watch = int(watch.get("pending_confirmation", 0) or 0)
    if pending_watch > 0:
        add_item(
            items,
            "watchlist_confirmation",
            f"{pending_watch} watchlist candidates pending",
            "pending_user_confirmation",
            "normal",
            "watchlist_review",
            {},
            "Confirm add to watchlist or ignore"
        )

    # Portfolio reconciliation warnings
    recon = load_json(SOURCES["portfolio_reconciliation"], {})
    prompt_required = int(recon.get("prompt_required_count", 0) or 0)
    if prompt_required > 0:
        add_item(
            items,
            "portfolio_reconciliation_review",
            f"{prompt_required} reconciliation items need review",
            "needs_review",
            "high",
            "portfolio_reconciliation_pipeline",
            {
                "safe_to_apply": recon.get("safe_to_apply_count"),
                "auto_applied": recon.get("auto_applied_count"),
                "closed_history": recon.get("closed_history_count")
            },
            "Review reconciliation before relying on tax/account outputs"
        )

    return items


def main():
    items = build_queue()

    counts = {}
    for item in items:
        counts[item["item_type"]] = counts.get(item["item_type"], 0) + 1

    high = len([x for x in items if x.get("priority") == "high"])

    payload = {
        "timestamp": now_utc(),
        "total_items": len(items),
        "high_priority": high,
        "counts": counts,
        "items": items,
        "policy": {
            "no_raw_data_on_mobile": True,
            "unverified_sources": "Stored as thesis/research leads until verified.",
            "official_or_personal_sources": "Usable after user confirmation.",
            "advisory_only": True
        }
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    DB_JSON.parent.mkdir(parents=True, exist_ok=True)

    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    DB_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = []
    lines.append("# Universal Action Queue")
    lines.append("")
    lines.append(f"Created: {payload['timestamp']}")
    lines.append(f"- Total items: {payload['total_items']}")
    lines.append(f"- High priority: {payload['high_priority']}")
    lines.append("")
    lines.append("## Queue Summary")
    for k, v in counts.items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Items")
    for item in items[:120]:
        lines.append(f"- [{item.get('priority')}] {item.get('title')} — {item.get('action')}")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "total_items": payload["total_items"],
        "high_priority": payload["high_priority"],
        "json": str(OUT_JSON)
    }, indent=2))


if __name__ == "__main__":
    main()
