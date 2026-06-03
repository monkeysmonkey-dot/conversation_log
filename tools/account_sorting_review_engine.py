import csv
import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]

RECON = BASE / "features" / "latest_portfolio_reconciliation.json"
OUT_CSV = BASE / "data" / "account_sorting_review.csv"
OUT_JSON = BASE / "features" / "latest_account_sorting_review.json"
OUT_MD = BASE / "reports" / "daily" / "latest_account_sorting_review.md"

VALID_ACCOUNT_TYPES = [
    "Taxable / Cash",
    "TFSA",
    "RRSP",
    "FHSA",
    "RESP",
    "Company Retirement",
    "Watchlist",
    "Closed / History",
    "Ignore",
    "Needs Sorting"
]


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def safe_float(value):
    try:
        if value in [None, ""]:
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def main():
    recon = load_json(RECON, {})
    active = recon.get("active_candidates_detail", [])
    needs_review = recon.get("needs_review_detail", [])
    closed = recon.get("closed_detail", [])

    rows = []

    for item in active:
        rows.append({
            "symbol": item.get("symbol", ""),
            "source_account_name": item.get("source_account_name", ""),
            "current_account_type": item.get("account_type", "Needs Sorting"),
            "assigned_account_type": "Needs Sorting",
            "currency": item.get("currency", ""),
            "quantity": item.get("preferred_quantity", ""),
            "average_cost": item.get("preferred_average_cost", ""),
            "cost_basis": item.get("preferred_cost_basis", ""),
            "confidence": item.get("confidence", ""),
            "status": item.get("status", ""),
            "review_action": "assign_account",
            "notes": ""
        })

    for item in needs_review:
        rows.append({
            "symbol": item.get("symbol", ""),
            "source_account_name": item.get("source_account_name", ""),
            "current_account_type": item.get("account_type", "Needs Sorting"),
            "assigned_account_type": "Needs Sorting",
            "currency": item.get("currency", ""),
            "quantity": item.get("preferred_quantity", ""),
            "average_cost": item.get("preferred_average_cost", ""),
            "cost_basis": item.get("preferred_cost_basis", ""),
            "confidence": item.get("confidence", ""),
            "status": item.get("status", ""),
            "review_action": "review_required",
            "notes": item.get("prompt_reason", "")
        })

    for item in closed:
        rows.append({
            "symbol": item.get("symbol", ""),
            "source_account_name": item.get("source_account_name", ""),
            "current_account_type": item.get("account_type", "Closed / History"),
            "assigned_account_type": "Closed / History",
            "currency": item.get("currency", ""),
            "quantity": item.get("signed_net_qty", 0),
            "average_cost": "",
            "cost_basis": "",
            "confidence": item.get("confidence", ""),
            "status": item.get("status", ""),
            "review_action": "closed_history",
            "notes": ""
        })

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    fields = [
        "symbol",
        "source_account_name",
        "current_account_type",
        "assigned_account_type",
        "currency",
        "quantity",
        "average_cost",
        "cost_basis",
        "confidence",
        "status",
        "review_action",
        "notes"
    ]

    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    payload = {
        "timestamp": now_utc(),
        "rows": len(rows),
        "valid_account_types": VALID_ACCOUNT_TYPES,
        "csv": str(OUT_CSV),
        "instructions": "Edit assigned_account_type for each row, then run account_sorting_apply_engine.py.",
        "advisory_only": True
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = []
    lines.append("# Account Sorting Review")
    lines.append("")
    lines.append(f"Created: {payload['timestamp']}")
    lines.append(f"- Rows to review: {payload['rows']}")
    lines.append(f"- Review CSV: {payload['csv']}")
    lines.append("")
    lines.append("## Valid Account Types")
    for acct in VALID_ACCOUNT_TYPES:
        lines.append(f"- {acct}")
    lines.append("")
    lines.append("## Instructions")
    lines.append("- Open data/account_sorting_review.csv")
    lines.append("- Fill assigned_account_type for each active holding")
    lines.append("- Valid values: Taxable / Cash, TFSA, RRSP, FHSA, RESP, Company Retirement, Watchlist, Closed / History, Ignore")
    lines.append("- Then run: py tools/account_sorting_apply_engine.py")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "rows": len(rows),
        "csv": str(OUT_CSV),
        "json": str(OUT_JSON)
    }, indent=2))


if __name__ == "__main__":
    main()
