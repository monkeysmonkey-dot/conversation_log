
import json
import subprocess
import sys
import os
import time
from pathlib import Path
from datetime import datetime, timezone, time

BASE = Path(__file__).resolve().parents[1]

OUT_JSON = BASE / "features" / "latest_bring_up_to_speed.json"
OUT_MD = BASE / "reports" / "daily" / "latest_bring_up_to_speed.md"
# OpenRouter / LLM throttle settings.
# OpenRouter free model variants can be limited to 20 requests/minute.
# Keep the manual catch-up conservative so agent-heavy workflows do not burst.
OPENROUTER_THROTTLE_ENABLED = os.environ.get("HERMES_OPENROUTER_THROTTLE", "1") == "1"
OPENROUTER_MIN_DELAY_SECONDS = float(os.environ.get("HERMES_OPENROUTER_MIN_DELAY_SECONDS", "3.25"))
OPENROUTER_RATE_LIMIT_BACKOFF_SECONDS = float(os.environ.get("HERMES_OPENROUTER_RATE_LIMIT_BACKOFF_SECONDS", "20"))
OPENROUTER_MAX_RETRIES = int(os.environ.get("HERMES_OPENROUTER_MAX_RETRIES", "2"))

SCHEDULE_STATUS_JSON = BASE / "features" / "latest_manual_schedule_status.json"
SCHEDULE_STATUS_MD = BASE / "reports" / "daily" / "latest_manual_schedule_status.md"


# Local schedule windows. This uses the computer's local time.
SCHEDULE_BLOCKS = [
    {
        "key": "macro_0600",
        "label": "06:00 Macro",
        "days": "weekday",
        "time": "06:00",
        "tools": [
            ("FX Rates", "tools/fx_rate_engine.py"),
            ("Market Console Trends", "tools/market_console_trend_engine.py"),
            ("Sector / ETF Flow", "tools/sector_etf_flow_engine.py"),
            ("Risk Sentiment", "tools/risk_sentiment_engine.py"),
            ("Sector Flow Deep Dive", "tools/sector_flow_deep_dive_engine.py"),
            ("Theme Rotation Intelligence", "tools/theme_rotation_intelligence_engine.py"),
            ("Opportunity Fit", "tools/opportunity_fit_engine.py"),
            ("Opportunity Fit Report", "tools/opportunity_fit_report_engine.py"),
            ("System Status", "tools/system_status_engine.py"),
            ("Universal Action Queue", "tools/universal_action_queue_engine.py"),
            ("Mobile Console Summary", "tools/mobile_console_summary_engine.py"),
            ("Agent Chat Router", "tools/agent_chat_router.py"),
        ],
    },
    {
        "key": "premarket_0700",
        "label": "07:00 Premarket",
        "days": "weekday",
        "time": "07:00",
        "tools": [
            ("Document Intake", "tools/document_intake_engine.py"),
            ("Document Router", "tools/document_router_engine.py"),
            ("Thesis Source Intake", "tools/thesis_source_intake_engine.py"),
            ("Portfolio CSV Import", "tools/portfolio_csv_import_engine.py"),
            ("Portfolio Reconciliation Pipeline", "tools/portfolio_reconciliation_pipeline.py"),
            ("Account Sorting Review", "tools/account_sorting_review_engine.py"),
            ("Account Sorting Apply", "tools/account_sorting_apply_engine.py"),
            ("Watchlist Review", "tools/watchlist_review_engine.py"),
            ("Account Portfolio Sync", "tools/sync_account_portfolio_snapshot.py"),
            ("Price Verification", "tools/price_fallback_engine.py"),
            ("Decision Data", "tools/decision_data_engine.py"),
            ("Decision Replay", "tools/decision_replay_engine.py"),
            ("Decision Replay Interpreter", "tools/decision_replay_interpreter.py"),
            ("Sector / ETF Flow", "tools/sector_etf_flow_engine.py"),
            ("Risk Sentiment", "tools/risk_sentiment_engine.py"),
            ("Sector Flow Deep Dive", "tools/sector_flow_deep_dive_engine.py"),
            ("Theme Rotation Intelligence", "tools/theme_rotation_intelligence_engine.py"),
            ("Opportunity Fit", "tools/opportunity_fit_engine.py"),
            ("Opportunity Fit Report", "tools/opportunity_fit_report_engine.py"),
            ("System Status", "tools/system_status_engine.py"),
        ],
    },
    {
        "key": "midday_1200",
        "label": "12:00 Midday",
        "days": "weekday",
        "time": "12:00",
        "tools": [
            ("Price Verification", "tools/price_fallback_engine.py"),
            ("Market Console Trends", "tools/market_console_trend_engine.py"),
            ("Sector / ETF Flow", "tools/sector_etf_flow_engine.py"),
            ("Risk Sentiment", "tools/risk_sentiment_engine.py"),
            ("Sector Flow Deep Dive", "tools/sector_flow_deep_dive_engine.py"),
            ("Theme Rotation Intelligence", "tools/theme_rotation_intelligence_engine.py"),
            ("Opportunity Fit", "tools/opportunity_fit_engine.py"),
            ("Opportunity Fit Report", "tools/opportunity_fit_report_engine.py"),
            ("System Status", "tools/system_status_engine.py"),
        ],
    },
    {
        "key": "afterhours_1600",
        "label": "16:00 After Hours",
        "days": "weekday",
        "time": "16:00",
        "tools": [
            ("Account Portfolio Sync", "tools/sync_account_portfolio_snapshot.py"),
            ("Price Verification", "tools/price_fallback_engine.py"),
            ("Decision Data", "tools/decision_data_engine.py"),
            ("Decision Replay", "tools/decision_replay_engine.py"),
            ("Decision Replay Interpreter", "tools/decision_replay_interpreter.py"),
            ("Sector / ETF Flow", "tools/sector_etf_flow_engine.py"),
            ("Risk Sentiment", "tools/risk_sentiment_engine.py"),
            ("Sector Flow Deep Dive", "tools/sector_flow_deep_dive_engine.py"),
            ("Theme Rotation Intelligence", "tools/theme_rotation_intelligence_engine.py"),
            ("Opportunity Fit", "tools/opportunity_fit_engine.py"),
            ("Opportunity Fit Report", "tools/opportunity_fit_report_engine.py"),
            ("Tax Advisor", "tools/tax_advisor_engine.py"),
            ("System Status", "tools/system_status_engine.py"),
        ],
    },
    {
        "key": "saturday_theme_0900",
        "label": "09:00 Saturday Theme",
        "days": "saturday",
        "time": "09:00",
        "tools": [
            ("Document Intake", "tools/document_intake_engine.py"),
            ("Document Router", "tools/document_router_engine.py"),
            ("Market Console Trends", "tools/market_console_trend_engine.py"),
            ("Sector / ETF Flow", "tools/sector_etf_flow_engine.py"),
            ("Risk Sentiment", "tools/risk_sentiment_engine.py"),
            ("Sector Flow Deep Dive", "tools/sector_flow_deep_dive_engine.py"),
            ("Theme Rotation Intelligence", "tools/theme_rotation_intelligence_engine.py"),
            ("Opportunity Fit", "tools/opportunity_fit_engine.py"),
            ("Opportunity Fit Report", "tools/opportunity_fit_report_engine.py"),
            ("Agent Chat Ideas", "tools/agent_chat_idea_engine.py"),
            ("Agent Council Brainstorm", "tools/agent_council_brainstorm_engine.py"),
            ("System Status", "tools/system_status_engine.py"),
        ],
    },
    {
        "key": "sunday_planning_0900",
        "label": "09:00 Sunday Planning",
        "days": "sunday",
        "time": "09:00",
        "tools": [
            ("FX Rates", "tools/fx_rate_engine.py"),
            ("Document Intake", "tools/document_intake_engine.py"),
            ("Document Router", "tools/document_router_engine.py"),
            ("Account Portfolio Sync", "tools/sync_account_portfolio_snapshot.py"),
            ("Price Verification", "tools/price_fallback_engine.py"),
            ("Decision Data", "tools/decision_data_engine.py"),
            ("Decision Replay", "tools/decision_replay_engine.py"),
            ("Decision Replay Interpreter", "tools/decision_replay_interpreter.py"),
            ("Mutual Fund Analysis", "tools/mutual_fund_analysis_engine.py"),
            ("Mutual Fund Review Schedule", "tools/mutual_fund_review_scheduler.py"),
            ("Tax Advisor", "tools/tax_advisor_engine.py"),
            ("Sector / ETF Flow", "tools/sector_etf_flow_engine.py"),
            ("Risk Sentiment", "tools/risk_sentiment_engine.py"),
            ("Sector Flow Deep Dive", "tools/sector_flow_deep_dive_engine.py"),
            ("Theme Rotation Intelligence", "tools/theme_rotation_intelligence_engine.py"),
            ("Opportunity Fit", "tools/opportunity_fit_engine.py"),
            ("Opportunity Fit Report", "tools/opportunity_fit_report_engine.py"),
            ("Agent Chat Ideas", "tools/agent_chat_idea_engine.py"),
            ("Agent Council Brainstorm", "tools/agent_council_brainstorm_engine.py"),
            ("System Status", "tools/system_status_engine.py"),
        ],
    },
]

# Always run these first so downstream engines have fresh inputs.
CORE_DEPENDENCIES = [
    ("FX Rates", "tools/fx_rate_engine.py"),
    ("Document Intake", "tools/document_intake_engine.py"),
    ("Document Router", "tools/document_router_engine.py"),
]

# Always run these at the end to refresh the current intelligence stack.
FINAL_INTELLIGENCE_STACK = [
    ("Sector / ETF Flow", "tools/sector_etf_flow_engine.py"),
    ("Risk Sentiment", "tools/risk_sentiment_engine.py"),
    ("Sector Flow Deep Dive", "tools/sector_flow_deep_dive_engine.py"),
    ("Theme Rotation Intelligence", "tools/theme_rotation_intelligence_engine.py"),
    ("Opportunity Fit", "tools/opportunity_fit_engine.py"),
    ("Opportunity Fit Report", "tools/opportunity_fit_report_engine.py"),
    ("System Status", "tools/system_status_engine.py"),
]


def now_local():
    return datetime.now()


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def parse_hhmm(value):
    hour, minute = value.split(":")
    return time(int(hour), int(minute))


def day_matches(rule, dt):
    # Monday = 0, Sunday = 6
    weekday = dt.weekday()

    if rule == "weekday":
        return weekday < 5
    if rule == "saturday":
        return weekday == 5
    if rule == "sunday":
        return weekday == 6
    if rule == "daily":
        return True

    return False


def due_blocks(dt):
    due = []

    for block in SCHEDULE_BLOCKS:
        if not day_matches(block.get("days"), dt):
            continue

        scheduled_time = parse_hhmm(block.get("time"))
        scheduled_dt = datetime.combine(dt.date(), scheduled_time)

        if dt >= scheduled_dt:
            age_minutes = int((dt - scheduled_dt).total_seconds() // 60)
            due.append({
                "key": block["key"],
                "label": block["label"],
                "scheduled_time": block["time"],
                "age_minutes": age_minutes,
                "tools": block["tools"],
            })

    return due


def dedupe_tools(tool_lists):
    seen = set()
    out = []

    for tools in tool_lists:
        for name, rel_path in tools:
            key = rel_path.lower().replace("\\", "/")
            if key in seen:
                continue
            seen.add(key)
            out.append((name, rel_path))

    return out



def looks_rate_limited(text):
    blob = str(text or "").lower()
    needles = [
        "429",
        "too many requests",
        "rate limit",
        "rate-limited",
        "ratelimit",
        "you are being rate limited",
        "provider rate limit",
        "model rate limit",
        "openrouter"
    ]
    return any(x in blob for x in needles)


def throttle_pause(reason=""):
    if not OPENROUTER_THROTTLE_ENABLED:
        return

    if OPENROUTER_MIN_DELAY_SECONDS <= 0:
        return

    print(f"[throttle] waiting {OPENROUTER_MIN_DELAY_SECONDS:.2f}s {reason}".strip())
    time.sleep(OPENROUTER_MIN_DELAY_SECONDS)



def run_task(name, rel_path):
    path = BASE / rel_path

    if not path.exists():
        return {
            "task": name,
            "tool": rel_path,
            "status": "skipped",
            "reason": "tool missing",
            "throttle_enabled": OPENROUTER_THROTTLE_ENABLED
        }

    attempts = 0
    last_reason = ""

    while attempts <= OPENROUTER_MAX_RETRIES:
        attempts += 1

        try:
            throttle_pause(f"before {name}")

            env = os.environ.copy()
            env["HERMES_OPENROUTER_THROTTLE"] = "1" if OPENROUTER_THROTTLE_ENABLED else "0"
            env["HERMES_OPENROUTER_MIN_DELAY_SECONDS"] = str(OPENROUTER_MIN_DELAY_SECONDS)
            env["HERMES_OPENROUTER_RATE_LIMIT_BACKOFF_SECONDS"] = str(OPENROUTER_RATE_LIMIT_BACKOFF_SECONDS)
            env["HERMES_OPENROUTER_MAX_RETRIES"] = str(OPENROUTER_MAX_RETRIES)

            kwargs = {
                "cwd": BASE,
                "capture_output": True,
                "text": True,
                "timeout": 1200,
                "env": env,
            }

            if hasattr(subprocess, "CREATE_NO_WINDOW"):
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            result = subprocess.run([sys.executable, str(path)], **kwargs)

            combined = ((result.stderr or "") + "\n" + (result.stdout or ""))

            if result.returncode == 0:
                throttle_pause(f"after {name}")
                return {
                    "task": name,
                    "tool": rel_path,
                    "status": "complete",
                    "returncode": result.returncode,
                    "attempts": attempts,
                    "reason": "ok",
                    "throttle_enabled": OPENROUTER_THROTTLE_ENABLED
                }

            last_reason = combined[-1800:]

            if looks_rate_limited(combined) and attempts <= OPENROUTER_MAX_RETRIES:
                wait = OPENROUTER_RATE_LIMIT_BACKOFF_SECONDS * attempts
                print(f"[rate-limit] {name} appears rate limited. Waiting {wait:.1f}s before retry {attempts}/{OPENROUTER_MAX_RETRIES}.")
                time.sleep(wait)
                continue

            throttle_pause(f"after {name}")
            return {
                "task": name,
                "tool": rel_path,
                "status": "error",
                "returncode": result.returncode,
                "attempts": attempts,
                "reason": last_reason,
                "throttle_enabled": OPENROUTER_THROTTLE_ENABLED
            }

        except Exception as e:
            last_reason = str(e)

            if looks_rate_limited(last_reason) and attempts <= OPENROUTER_MAX_RETRIES:
                wait = OPENROUTER_RATE_LIMIT_BACKOFF_SECONDS * attempts
                print(f"[rate-limit] {name} exception appears rate limited. Waiting {wait:.1f}s before retry.")
                time.sleep(wait)
                continue

            return {
                "task": name,
                "tool": rel_path,
                "status": "error",
                "attempts": attempts,
                "reason": last_reason,
                "throttle_enabled": OPENROUTER_THROTTLE_ENABLED
            }



def write_manual_schedule_status(local_now, due, results, payload):
    result_by_tool = {}

    for item in results:
        key = str(item.get("tool", "")).lower().replace("\\", "/")
        result_by_tool[key] = item

    blocks = []

    for block in SCHEDULE_BLOCKS:
        block_tools = block.get("tools", [])
        completed = 0
        skipped = 0
        errors = 0
        missing = 0

        for name, rel_path in block_tools:
            tool_key = rel_path.lower().replace("\\", "/")
            result = result_by_tool.get(tool_key)

            if result is None:
                missing += 1
                continue

            status = result.get("status")

            if status == "complete":
                completed += 1
            elif status == "skipped":
                skipped += 1
            elif status == "error":
                errors += 1

        # Manual Bring Up To Speed means all scheduler blocks are considered refreshed
        # if their available tools completed without errors.
        if errors == 0 and completed > 0:
            status = "complete"
            icon = "✅"
            color = "green"
        elif errors > 0:
            status = "needs_review"
            icon = "⚠️"
            color = "yellow"
        elif completed == 0:
            status = "not_run"
            icon = "🔴"
            color = "red"
        else:
            status = "not_due"
            icon = "⚪"
            color = "gray"

        blocks.append({
            "key": block.get("key"),
            "label": block.get("label"),
            "scheduled_time": block.get("time"),
            "status": status,
            "status_icon": icon,
            "color": color,
            "last_checked_local": local_now.isoformat(),
            "behind_minutes": None,
            "tasks_total": len(block_tools),
            "tasks_complete": completed,
            "tasks_skipped": skipped,
            "tasks_errors": errors,
            "tasks_missing_from_run": missing
        })

    status_payload = {
        "timestamp": now_utc(),
        "local_time": local_now.isoformat(),
        "source": "bring_up_to_speed_engine.py",
        "catchup_mode": payload.get("catchup_mode"),
        "overall_status": payload.get("status"),
        "blocks": blocks,
        "advisory_only": True
    }

    SCHEDULE_STATUS_JSON.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULE_STATUS_JSON.write_text(json.dumps(status_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = []
    lines.append("# Manual Scheduler Status")
    lines.append("")
    lines.append(f"Created UTC: {status_payload['timestamp']}")
    lines.append(f"Local time: {status_payload['local_time']}")
    lines.append(f"Overall status: {status_payload['overall_status']}")
    lines.append("")
    lines.append("## Blocks")

    for block in blocks:
        lines.append(
            f"- {block.get('status_icon')} {block.get('label')}: {block.get('status')} "
            f"| complete {block.get('tasks_complete')}/{block.get('tasks_total')} "
            f"| errors {block.get('tasks_errors')}"
        )

    SCHEDULE_STATUS_MD.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULE_STATUS_MD.write_text("\n".join(lines), encoding="utf-8")

    return status_payload


def main():

    local_now = now_local()
    due = due_blocks(local_now)

    # Manual Bring Up To Speed means full manual scheduler catch-up.
    # Run every schedule block so manual schedule state can be updated green when successful.
    run_groups = [CORE_DEPENDENCIES] + [block["tools"] for block in SCHEDULE_BLOCKS] + [FINAL_INTELLIGENCE_STACK]
    catchup_mode = "manual_full_scheduler_catchup"

    tasks = dedupe_tools(run_groups)

    results = []
    for name, rel_path in tasks:
        results.append(run_task(name, rel_path))

    complete = len([r for r in results if r.get("status") == "complete"])
    skipped = len([r for r in results if r.get("status") == "skipped"])
    errors = len([r for r in results if r.get("status") == "error"])

    payload = {
        "timestamp": now_utc(),
        "local_time": local_now.isoformat(),
        "catchup_mode": catchup_mode,
        "status": "complete" if errors == 0 else "needs_review",
        "due_blocks": [
            {
                "key": block["key"],
                "label": block["label"],
                "scheduled_time": block["scheduled_time"],
                "age_minutes": block["age_minutes"],
            }
            for block in due
        ],
        "tasks_planned": len(tasks),
        "complete": complete,
        "skipped": skipped,
        "errors": errors,
        "results": results,
        "advisory_only": True,
        "openrouter_throttle": {
            "enabled": OPENROUTER_THROTTLE_ENABLED,
            "min_delay_seconds": OPENROUTER_MIN_DELAY_SECONDS,
            "rate_limit_backoff_seconds": OPENROUTER_RATE_LIMIT_BACKOFF_SECONDS,
            "max_retries": OPENROUTER_MAX_RETRIES
        }
    }

    schedule_status_payload = write_manual_schedule_status(local_now, due, results, payload)

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = []
    lines.append("# Bring Up To Speed")
    lines.append("")
    lines.append(f"Created UTC: {payload['timestamp']}")
    lines.append(f"Local time: {payload['local_time']}")
    lines.append(f"Mode: {payload['catchup_mode']}")
    lines.append(f"Status: {payload['status']}")
    lines.append(f"- Tasks planned: {payload['tasks_planned']}")
    lines.append(f"- Complete: {complete}")
    lines.append(f"- Skipped: {skipped}")
    lines.append(f"- Errors: {errors}")
    lines.append("")
    lines.append("## Due / Missed Schedule Blocks")

    if payload["due_blocks"]:
        for block in payload["due_blocks"]:
            lines.append(
                f"- {block['label']} | scheduled {block['scheduled_time']} | behind by {block['age_minutes']} minutes"
            )
    else:
        lines.append("- No scheduled block is currently behind. Core refresh was run only.")

    lines.append("")
    lines.append("## Tasks")
    for r in results:
        lines.append(f"- {r.get('task')}: {r.get('status')}")

    if errors:
        lines.append("")
        lines.append("## Errors")
        for r in results:
            if r.get("status") == "error":
                lines.append(f"### {r.get('task')}")
                lines.append(str(r.get("reason", ""))[:1600])

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": payload["status"],
        "mode": payload["catchup_mode"],
        "due_blocks": [b["label"] for b in payload["due_blocks"]],
        "tasks_planned": payload["tasks_planned"],
        "complete": complete,
        "skipped": skipped,
        "errors": errors,
        "json": str(OUT_JSON)
    }, indent=2))


if __name__ == "__main__":
    main()
