import csv
import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]

SORTING_CSV = BASE / "data" / "account_sorting_review.csv"
PORTFOLIO = BASE / "data" / "portfolio_snapshot.json"
SORTING_MAP = BASE / "data" / "account_sorting_map.json"

OUT_JSON = BASE / "features" / "latest_account_sorting_apply.json"
OUT_MD = BASE / "reports" / "daily" / "latest_account_sorting_apply.md"

VALID_ACCOUNT_TYPES = {
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
}


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


def safe_float(value):
    try:
        if value in [None, ""]:
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def read_csv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as f:
        return list(csv.DictReader(f))


def main():
    rows = read_csv(SORTING_CSV)
    portfolio = load_json(PORTFOLIO, {})
    existing_map = load_json(SORTING_MAP, {"mappings": []})

    positions = portfolio.get("positions", {})
    if not isinstance(positions, dict):
        positions = {}

    mappings = []
    applied = 0
    still_needs_sorting = 0
    ignored = 0
    invalid = []

    for row in rows:
        symbol = clean(row.get("symbol")).upper()
        source_account = clean(row.get("source_account_name"))
        assigned = clean(row.get("assigned_account_type")) or "Needs Sorting"
        currency = clean(row.get("currency")).upper()

        if not symbol:
            continue

        if assigned not in VALID_ACCOUNT_TYPES:
            invalid.append({
                "symbol": symbol,
                "assigned_account_type": assigned,
                "reason": "Invalid account type."
            })
            continue

        mapping = {
            "symbol": symbol,
            "source_account_name": source_account,
            "assigned_account_type": assigned,
            "currency": currency,
            "updated_at": now_utc()
        }
        mappings.append(mapping)

        if assigned == "Ignore":
            ignored += 1
            continue

        if assigned == "Needs Sorting":
            still_needs_sorting += 1
            continue

        # Find matching positions and rewrite key/account type.
        old_keys = [
            k for k, v in positions.items()
            if str(v.get("symbol", v.get("ticker", ""))).upper() == symbol
            and str(v.get("currency", "")).upper() == currency
        ]

        for old_key in old_keys:
            item = positions.pop(old_key)
            item["account_type"] = assigned
            item["source_account_name"] = source_account
            item["needs_account_sorting"] = False if assigned not in ["Needs Sorting"] else True
            item["account_sorting_confirmed"] = assigned not in ["Needs Sorting"]
            item["updated_at"] = now_utc()

            new_key = f"{symbol}|{assigned}|{currency}"
            positions[new_key] = item
            applied += 1

    portfolio["positions"] = positions
    portfolio["updated_at"] = now_utc()
    portfolio["account_sorting_updated_at"] = now_utc()
    portfolio["source"] = "account_sorting_apply_engine"
    portfolio["advisory_only"] = True

    existing_map["mappings"] = mappings
    existing_map["updated_at"] = now_utc()
    existing_map["valid_account_types"] = sorted(list(VALID_ACCOUNT_TYPES))

    if PORTFOLIO.exists():
        backup = PORTFOLIO.with_name("portfolio_snapshot_before_account_sorting_apply.json")
        backup.write_text(PORTFOLIO.read_text(encoding="utf-8", errors="ignore"), encoding="utf-8")

    save_json(PORTFOLIO, portfolio)
    save_json(SORTING_MAP, existing_map)

    payload = {
        "timestamp": now_utc(),
        "status": "needs_review" if invalid or still_needs_sorting else "complete",
        "rows_read": len(rows),
        "applied_position_updates": applied,
        "still_needs_sorting": still_needs_sorting,
        "ignored": ignored,
        "invalid_rows": invalid,
        "portfolio_file": str(PORTFOLIO),
        "sorting_map": str(SORTING_MAP),
        "advisory_only": True
    }

    save_json(OUT_JSON, payload)

    lines = []
    lines.append("# Account Sorting Apply")
    lines.append("")
    lines.append(f"Created: {payload['timestamp']}")
    lines.append(f"- Status: {payload['status']}")
    lines.append(f"- Rows read: {payload['rows_read']}")
    lines.append(f"- Applied position updates: {payload['applied_position_updates']}")
    lines.append(f"- Still needs sorting: {payload['still_needs_sorting']}")
    lines.append(f"- Ignored: {payload['ignored']}")
    lines.append(f"- Invalid rows: {len(payload['invalid_rows'])}")

    if invalid:
        lines.append("")
        lines.append("## Invalid Rows")
        for item in invalid:
            lines.append(f"- {item['symbol']} | {item['assigned_account_type']} | {item['reason']}")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": payload["status"],
        "rows_read": payload["rows_read"],
        "applied_position_updates": payload["applied_position_updates"],
        "still_needs_sorting": payload["still_needs_sorting"],
        "invalid_rows": len(payload["invalid_rows"]),
        "json": str(OUT_JSON)
    }, indent=2))


if __name__ == "__main__":
    main()
