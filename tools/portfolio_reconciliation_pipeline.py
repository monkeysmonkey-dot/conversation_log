import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]

RECON = BASE / "features" / "latest_portfolio_reconciliation.json"
PORTFOLIO = BASE / "data" / "portfolio_snapshot.json"

OUT_JSON = BASE / "features" / "latest_portfolio_reconciliation_pipeline.json"
OUT_MD = BASE / "reports" / "daily" / "latest_portfolio_reconciliation_pipeline.md"


PIPELINE = [
    ("Portfolio CSV Import", "tools/portfolio_csv_import_engine.py"),
    ("Portfolio Reconciliation Agent", "tools/portfolio_reconciliation_agent.py"),
    ("Portfolio Grouped Preview", "tools/portfolio_grouped_preview_engine.py"),
    ("Watchlist Review", "tools/watchlist_review_engine.py"),
]


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


def run_tool(label, rel_path):
    path = BASE / rel_path

    if not path.exists():
        return {
            "label": label,
            "tool": rel_path,
            "status": "skipped",
            "reason": "tool missing"
        }

    kwargs = {
        "cwd": BASE,
        "capture_output": True,
        "text": True,
        "timeout": 900,
    }

    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

    result = subprocess.run([sys.executable, str(path)], **kwargs)

    if result.returncode == 0:
        return {
            "label": label,
            "tool": rel_path,
            "status": "complete",
            "returncode": result.returncode,
            "stdout_tail": (result.stdout or "")[-1200:],
            "stderr_tail": (result.stderr or "")[-1200:]
        }

    return {
        "label": label,
        "tool": rel_path,
        "status": "error",
        "returncode": result.returncode,
        "stdout_tail": (result.stdout or "")[-1200:],
        "stderr_tail": (result.stderr or "")[-1200:]
    }


def split_reconciliation_items(recon):
    active = recon.get("active_candidates_detail", [])
    needs_review = recon.get("needs_review_detail", [])
    closed = recon.get("closed_detail", [])
    watch = recon.get("watchlist_only_detail", [])

    safe_to_apply = []
    prompt_required = []

    for item in active:
        confidence = item.get("confidence", "")
        needs_sorting = bool(item.get("needs_account_sorting"))

        # Safe math, but account sorting may still be needed.
        if confidence == "high" and not needs_sorting:
            safe_to_apply.append(item)
        else:
            prompt_required.append({
                **item,
                "prompt_reason": "Needs account sorting or confidence is not high."
            })

    for item in needs_review:
        prompt_required.append({
            **item,
            "prompt_reason": "Reconciliation needs review."
        })

    return safe_to_apply, prompt_required, closed, watch


def apply_safe_positions(safe_items):
    portfolio = load_json(PORTFOLIO, {})
    positions = portfolio.get("positions", {})

    if not isinstance(positions, dict):
        positions = {}

    applied = 0

    for item in safe_items:
        key = f"{item.get('symbol')}|{item.get('account_type')}|{item.get('currency')}"
        old = positions.get(key) or positions.get(item.get("symbol"), {})

        current_price = float(old.get("current_price", 0) or 0)
        qty = float(item.get("preferred_quantity", 0) or 0)
        market_value = current_price * qty if current_price else 0

        positions[key] = {
            **old,
            "ticker": item.get("symbol"),
            "symbol": item.get("symbol"),
            "source_account_name": item.get("source_account_name"),
            "account_type": item.get("account_type"),
            "currency": item.get("currency"),
            "quantity": qty,
            "average_cost": item.get("preferred_average_cost"),
            "cost_basis": item.get("preferred_cost_basis"),
            "current_price": current_price,
            "market_value": market_value,
            "lot_count": item.get("lot_count"),
            "lots": item.get("lots", []),
            "needs_account_sorting": item.get("needs_account_sorting"),
            "reconciliation_method": item.get("preferred_method"),
            "reconciliation_confidence": item.get("confidence"),
            "source_type": "automated_reconciliation_pipeline",
            "updated_at": now_utc(),
            "advisory_only": True
        }

        applied += 1

    portfolio["positions"] = positions
    portfolio["updated_at"] = now_utc()
    portfolio["source"] = "portfolio_reconciliation_pipeline"
    portfolio["advisory_only"] = True

    if safe_items:
        backup = PORTFOLIO.with_name("portfolio_snapshot_before_auto_reconciliation_apply.json")
        if PORTFOLIO.exists():
            backup.write_text(PORTFOLIO.read_text(encoding="utf-8", errors="ignore"), encoding="utf-8")
        save_json(PORTFOLIO, portfolio)

    return applied


def main():
    run_results = []

    for label, rel_path in PIPELINE:
        run_results.append(run_tool(label, rel_path))

    errors = [x for x in run_results if x.get("status") == "error"]

    recon = load_json(RECON, {})
    safe_to_apply, prompt_required, closed, watch = split_reconciliation_items(recon)

    applied = apply_safe_positions(safe_to_apply)

    payload = {
        "timestamp": now_utc(),
        "status": "needs_review" if errors or prompt_required else "complete",
        "pipeline_results": run_results,
        "safe_to_apply_count": len(safe_to_apply),
        "auto_applied_count": applied,
        "prompt_required_count": len(prompt_required),
        "closed_history_count": len(closed),
        "watchlist_only_count": len(watch),
        "safe_to_apply": safe_to_apply,
        "prompt_required": prompt_required,
        "closed_history": closed,
        "watchlist_only": watch,
        "rules": {
            "auto_apply": "Only high-confidence active holdings with no account sorting required.",
            "prompt_user": "Account sorting, medium confidence, unknown/ambiguous transaction types, negative net shares, and watchlist candidates.",
            "math": "Buy transaction types are positive. Sell transaction types are negative. Net shares above zero means active holding."
        },
        "advisory_only": True
    }

    save_json(OUT_JSON, payload)

    lines = []
    lines.append("# Portfolio Reconciliation Pipeline")
    lines.append("")
    lines.append(f"Created: {payload['timestamp']}")
    lines.append(f"- Status: {payload['status']}")
    lines.append(f"- Safe to apply: {payload['safe_to_apply_count']}")
    lines.append(f"- Auto-applied: {payload['auto_applied_count']}")
    lines.append(f"- Prompt required: {payload['prompt_required_count']}")
    lines.append(f"- Closed/history: {payload['closed_history_count']}")
    lines.append(f"- Watchlist-only: {payload['watchlist_only_count']}")
    lines.append("")
    lines.append("## Pipeline Results")
    for r in run_results:
        lines.append(f"- {r.get('label')}: {r.get('status')}")

    lines.append("")
    lines.append("## Auto-Applied High-Confidence Holdings")
    if safe_to_apply:
        for item in safe_to_apply[:100]:
            lines.append(
                f"- {item.get('symbol')} | Qty {item.get('preferred_quantity')} | "
                f"Avg Cost {item.get('preferred_average_cost')} | "
                f"Account {item.get('account_type')} | Currency {item.get('currency')}"
            )
    else:
        lines.append("- None.")

    lines.append("")
    lines.append("## User Review Required")
    if prompt_required:
        for item in prompt_required[:100]:
            lines.append(
                f"- {item.get('symbol')} | Qty {item.get('preferred_quantity')} | "
                f"Account {item.get('account_type')} | Confidence {item.get('confidence')} | "
                f"Reason: {item.get('prompt_reason')}"
            )
    else:
        lines.append("- None.")

    lines.append("")
    lines.append("## Closed / History")
    if closed:
        for item in closed[:80]:
            lines.append(f"- {item.get('symbol')} | Net shares {item.get('signed_net_qty')} | Status {item.get('status')}")
    else:
        lines.append("- None.")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": payload["status"],
        "safe_to_apply": payload["safe_to_apply_count"],
        "auto_applied": payload["auto_applied_count"],
        "prompt_required": payload["prompt_required_count"],
        "closed_history": payload["closed_history_count"],
        "watchlist_only": payload["watchlist_only_count"],
        "json": str(OUT_JSON)
    }, indent=2))


if __name__ == "__main__":
    main()
