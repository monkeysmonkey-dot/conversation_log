import os
import json
import subprocess
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

BASE =YOUR_VALUE_HERE

SCHEDULE_PATH =YOUR_VALUE_HERE
BUDGET_PATH =YOUR_VALUE_HERE
MODEL_ASSIGN_PATH =YOUR_VALUE_HERE

STATUS_PATH =YOUR_VALUE_HERE
USAGE_LEDGER =YOUR_VALUE_HERE
MODEL_CACHE =YOUR_VALUE_HERE


def now_local():
    return datetime.now()


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding=YOUR_VALUE_HERE
    except Exception:
        return default


def save_json(path, data):
    Path(path).parent.mkdir(parents=YOUR_VALUE_HERE
    Path(path).write_text(json.dumps(data, indent=YOUR_VALUE_HERE


def ensure_default_configs():
    SCHEDULE_PATH.parent.mkdir(parents=YOUR_VALUE_HERE

    if not SCHEDULE_PATH.exists():
        schedule =YOUR_VALUE_HERE
            "cooldown_seconds": 90,
            "tasks": [
                {
                    "id": "daily_hermes_system",
                    "label": "Daily Hermes System / Premarket Scan",
                    "type": "weekday",
                    "time": "06:00",
                    "command": ["py", "run_hermes_system.py"],
                    "expected_minutes": 20,
                    "agent_group": "core_research"
                },
                {
                    "id": "premarket_regime_summary",
                    "label": "Premarket Regime Summary",
                    "type": "weekday",
                    "time": "07:00",
                    "command": ["py", "tools\\theme_wave_engine.py"],
                    "expected_minutes": 10,
                    "agent_group": "macro_theme"
                },
                {
                    "id": "midday_confirmation_scan",
                    "label": "Midday Confirmation Scan",
                    "type": "weekday",
                    "time": "12:00",
                    "command": ["py", "run_hermes_system.py"],
                    "expected_minutes": 20,
                    "agent_group": "confirmation"
                },
                {
                    "id": "afterhours_review",
                    "label": "After-Hours Review / Journal",
                    "type": "weekday",
                    "time": "16:00",
                    "command": ["py", "run_hermes_system.py"],
                    "expected_minutes": 20,
                    "agent_group": "journal_review"
                },
                {
                    "id": "saturday_relationship_expansion",
                    "label": "Saturday Relationship / Theme Expansion",
                    "type": "weekly",
                    "day": "SAT",
                    "time": "09:00",
                    "command": ["py", "workers\\saturday_relationship_expansion.py"],
                    "expected_minutes": 30,
                    "agent_group": "relationship_theme"
                },
                {
                    "id": "sunday_investment_planning",
                    "label": "Sunday Investment Planning",
                    "type": "weekly",
                    "day": "SUN",
                    "time": "09:00",
                    "command": ["py", "workers\\sunday_investment_planning.py"],
                    "expected_minutes": 30,
                    "agent_group": "investment_planning"
                }
            ]
        }
        save_json(SCHEDULE_PATH, schedule)

    if not BUDGET_PATH.exists():
        budget =YOUR_VALUE_HERE
            "daily_budget_usd": 2.50,
            "hard_stop_enabled": True,
            "flash_warning_threshold_pct": 90,
            "task_budgets_usd": {
                "daily_hermes_system": 0.50,
                "premarket_regime_summary": 0.25,
                "midday_confirmation_scan": 0.35,
                "afterhours_review": 0.35,
                "saturday_relationship_expansion": 0.75,
                "sunday_investment_planning": 0.75
            },
            "agent_raise_rules": {
                "enabled": True,
                "review_day": "SUN",
                "raise_pct_if_profitable_and_confirmed": 15,
                "cut_pct_if_underperforming": 10,
                "max_weekly_raise_pct": 30,
                "minimum_observations": 5
            }
        }
        save_json(BUDGET_PATH, budget)

    if not MODEL_ASSIGN_PATH.exists():
        models =YOUR_VALUE_HERE
            "global_default_model": "openrouter/auto",
            "allow_one_model_for_all_tasks": True,
            "model_assignments": {
                "daily_hermes_system": "openrouter/auto",
                "premarket_regime_summary": "openrouter/auto",
                "midday_confirmation_scan": "openrouter/auto",
                "afterhours_review": "openrouter/auto",
                "saturday_relationship_expansion": "openrouter/auto",
                "sunday_investment_planning": "openrouter/auto"
            },
            "task_requirements": {
                "daily_hermes_system": ["structured_output", "low_cost", "fast"],
                "premarket_regime_summary": ["macro_reasoning", "fast"],
                "midday_confirmation_scan": ["fast", "cheap"],
                "afterhours_review": ["journal_reasoning", "structured_output"],
                "saturday_relationship_expansion": ["deep_reasoning", "long_context", "relationship_mapping"],
                "sunday_investment_planning": ["deep_reasoning", "planning", "risk_analysis"]
            }
        }
        save_json(MODEL_ASSIGN_PATH, models)


def load_schedule():
    ensure_default_configs()
    return load_json(SCHEDULE_PATH, {"cooldown_seconds": 90, "tasks": []})


def load_budget():
    ensure_default_configs()
    return load_json(BUDGET_PATH, {})


def load_model_assignments():
    ensure_default_configs()
    return load_json(MODEL_ASSIGN_PATH, {})


def load_status():
    return load_json(STATUS_PATH, {"runs": {}, "last_task_finished_at": None})


def save_status(status):
    save_json(STATUS_PATH, status)


def parse_task_datetime(task, ref=YOUR_VALUE_HERE
    ref =YOUR_VALUE_HERE
    hh, mm =YOUR_VALUE_HERE
    return ref.replace(hour=YOUR_VALUE_HERE


def task_due_state(task, status):
    now =YOUR_VALUE_HERE
    runs =YOUR_VALUE_HERE
    task_id =YOUR_VALUE_HERE
    last =YOUR_VALUE_HERE
    last_date =YOUR_VALUE_HERE

    today_str =YOUR_VALUE_HERE
    target =YOUR_VALUE_HERE

    if task.get("type") =YOUR_VALUE_HERE
        day =YOUR_VALUE_HERE
        weekday_map =YOUR_VALUE_HERE
        target_day =YOUR_VALUE_HERE

        if target_day is None:
            return "pending"

        if now.weekday() !=YOUR_VALUE_HERE
            return "not_today"
    else:
        if now.weekday() >=YOUR_VALUE_HERE
            return "not_today"

    if last_date =YOUR_VALUE_HERE
        return "satisfied"

    if now >=YOUR_VALUE_HERE
        return "missed"

    return "pending"


def cooldown_remaining_seconds():
    schedule =YOUR_VALUE_HERE
    cooldown =YOUR_VALUE_HERE
    status =YOUR_VALUE_HERE
    last_finished =YOUR_VALUE_HERE

    if not last_finished:
        return 0

    try:
        last_dt =YOUR_VALUE_HERE
        elapsed =YOUR_VALUE_HERE
        remaining =YOUR_VALUE_HERE
        return max(0, int(remaining))
    except Exception:
        return 0


def today_usage_total():
    today =YOUR_VALUE_HERE
    total =YOUR_VALUE_HERE

    if not USAGE_LEDGER.exists():
        return 0.0

    for line in USAGE_LEDGER.read_text(encoding=YOUR_VALUE_HERE
        try:
            row =YOUR_VALUE_HERE
            if str(row.get("date")) =YOUR_VALUE_HERE
                total +=YOUR_VALUE_HERE
        except Exception:
            pass

    return round(total, 6)


def estimate_task_cost(task_id, model_id=YOUR_VALUE_HERE
    defaults =YOUR_VALUE_HERE
        "daily_hermes_system": 0.18,
        "premarket_regime_summary": 0.08,
        "midday_confirmation_scan": 0.12,
        "afterhours_review": 0.12,
        "saturday_relationship_expansion": 0.35,
        "sunday_investment_planning": 0.35
    }
    return float(defaults.get(task_id, 0.10))


def budget_check(task_id, estimated_cost):
    budget =YOUR_VALUE_HERE
    daily_budget =YOUR_VALUE_HERE
    task_budget =YOUR_VALUE_HERE
    used_today =YOUR_VALUE_HERE

    result =YOUR_VALUE_HERE
        "daily_budget_usd": daily_budget,
        "task_budget_usd": task_budget,
        "used_today_usd": used_today,
        "estimated_cost_usd": estimated_cost,
        "allowed": True,
        "reason": "ok",
        "warning": False
    }

    if task_budget is not None and estimated_cost > float(task_budget):
        result["allowed"] =YOUR_VALUE_HERE
        result["reason"] =YOUR_VALUE_HERE

    if daily_budget is not None and used_today + estimated_cost > float(daily_budget):
        result["allowed"] =YOUR_VALUE_HERE
        result["reason"] =YOUR_VALUE_HERE

    threshold =YOUR_VALUE_HERE
    if daily_budget is not None and (used_today + estimated_cost) >=YOUR_VALUE_HERE
        result["warning"] =YOUR_VALUE_HERE

    return result


def record_usage(task_id, model_id, estimated_cost):
    row =YOUR_VALUE_HERE
        "timestamp": now_local().isoformat(),
        "date": now_local().strftime("%Y-%m-%d"),
        "task_id": task_id,
        "model_id": model_id,
        "estimated_cost_usd": estimated_cost
    }

    USAGE_LEDGER.parent.mkdir(parents=YOUR_VALUE_HERE
    with open(USAGE_LEDGER, "a", encoding=YOUR_VALUE_HERE
        f.write(json.dumps(row, ensure_ascii=YOUR_VALUE_HERE


def run_task(task_id):
    schedule =YOUR_VALUE_HERE
    tasks =YOUR_VALUE_HERE

    if task_id not in tasks:
        return {"status": "error", "error": f"Unknown task_id {task_id}"}

    remaining =YOUR_VALUE_HERE
    if remaining > 0:
        return {
            "status": "cooldown",
            "cooldown_remaining_seconds": remaining
        }

    model_cfg =YOUR_VALUE_HERE
    model_id =YOUR_VALUE_HERE
        task_id,
        model_cfg.get("global_default_model", "openrouter/auto")
    )

    estimated =YOUR_VALUE_HERE
    budget =YOUR_VALUE_HERE

    if not budget.get("allowed", True):
        return {
            "status": "blocked_budget",
            "budget": budget
        }

    task =YOUR_VALUE_HERE
    cmd =YOUR_VALUE_HERE

    try:
        started =YOUR_VALUE_HERE

        r =YOUR_VALUE_HERE
            cmd,
            cwd=YOUR_VALUE_HERE
            capture_output=YOUR_VALUE_HERE
            text=YOUR_VALUE_HERE
            timeout=YOUR_VALUE_HERE
        )

        finished =YOUR_VALUE_HERE

        result =YOUR_VALUE_HERE
            "task_id": task_id,
            "label": task.get("label"),
            "status": "complete" if r.returncode =YOUR_VALUE_HERE
            "returncode": r.returncode,
            "started_at": started,
            "finished_at": finished,
            "stdout_tail": r.stdout[-3000:],
            "stderr_tail": r.stderr[-3000:],
            "model_id": model_id,
            "estimated_cost_usd": estimated,
            "budget": budget
        }

        status =YOUR_VALUE_HERE
        today_str =YOUR_VALUE_HERE
        status.setdefault("runs", {})[task_id] =YOUR_VALUE_HERE
            "date": today_str,
            "finished_at": finished,
            "status": result["status"]
        }
        status["last_task_finished_at"] =YOUR_VALUE_HERE
        save_status(status)

        record_usage(task_id, model_id, estimated)

        return result

    except Exception as e:
        return {
            "task_id": task_id,
            "status": "failed",
            "error": str(e)
        }


def classify_model(model):
    model_id =YOUR_VALUE_HERE
    name =YOUR_VALUE_HERE
    supported =YOUR_VALUE_HERE
    pricing =YOUR_VALUE_HERE

    prompt_price =YOUR_VALUE_HERE
    completion_price =YOUR_VALUE_HERE

    tags =YOUR_VALUE_HERE
    if str(prompt_price) in ["0", "0.0"] and str(completion_price) in ["0", "0.0"]:
        tags.append("free")

    lower =YOUR_VALUE_HERE

    if "flash" in lower or "mini" in lower or "lite" in lower:
        tags.append("flash/cheap")

    if "reason" in lower or "thinking" in lower or "think" in lower:
        tags.append("thinking/reasoning")

    if "tools" in supported:
        tags.append("tool-capable")

    if "response_format" in supported or "structured_outputs" in supported:
        tags.append("structured-output")

    if "web" in lower or "search" in lower:
        tags.append("web/special")

    return tags


def refresh_openrouter_models():
    import requests

    url =YOUR_VALUE_HERE
    headers =YOUR_VALUE_HERE

    api_key =YOUR_VALUE_HERE
    if api_key:
        headers["Authorization"] =YOUR_VALUE_HERE

    r =YOUR_VALUE_HERE
    r.raise_for_status()

    data =YOUR_VALUE_HERE
    models =YOUR_VALUE_HERE

    normalized =YOUR_VALUE_HERE
    for m in models:
        item =YOUR_VALUE_HERE
            "id": m.get("id"),
            "name": m.get("name", m.get("id")),
            "context_length": m.get("context_length"),
            "pricing": m.get("pricing", {}),
            "supported_parameters": m.get("supported_parameters", []),
            "tags": classify_model(m)
        }
        normalized.append(item)

    MODEL_CACHE.parent.mkdir(parents=YOUR_VALUE_HERE
    MODEL_CACHE.write_text(json.dumps({
        "refreshed_at": now_local().isoformat(),
        "models": normalized
    }, indent=YOUR_VALUE_HERE

    return normalized


def load_model_catalog():
    if MODEL_CACHE.exists():
        return load_json(MODEL_CACHE, {"models": []}).get("models", [])
    return []


def recommend_model_for_task(task_id):
    if task_id in ["saturday_relationship_expansion", "sunday_investment_planning"]:
        return {
            "recommendation": "Use reasoning / long-context model if budget allows. Use free/cheap model for drafts.",
            "preferred_tags": ["thinking/reasoning", "structured-output"]
        }

    if task_id in ["midday_confirmation_scan", "premarket_regime_summary"]:
        return {
            "recommendation": "Use fast/cheap or flash model.",
            "preferred_tags": ["flash/cheap", "free"]
        }

    return {
        "recommendation": "Use balanced model or OpenRouter auto.",
        "preferred_tags": ["structured-output", "flash/cheap"]
    }


if __name__ =YOUR_VALUE_HERE
    ensure_default_configs()
    print(json.dumps({
        "status": "ok",
        "schedule": str(SCHEDULE_PATH),
        "budget": str(BUDGET_PATH),
        "models": str(MODEL_ASSIGN_PATH)
    }, indent=YOUR_VALUE_HERE


def save_model_assignment(task_id, model_id):
    cfg =YOUR_VALUE_HERE

    cfg.setdefault("model_assignments", {})
    cfg["model_assignments"][task_id] =YOUR_VALUE_HERE

    save_json(MODEL_ASSIGN_PATH, cfg)

    return {
        "status": "saved",
        "task_id": task_id,
        "model_id": model_id,
        "path": str(MODEL_ASSIGN_PATH)
    }


def save_global_default_model(model_id):
    cfg =YOUR_VALUE_HERE

    cfg["global_default_model"] =YOUR_VALUE_HERE

    save_json(MODEL_ASSIGN_PATH, cfg)

    return {
        "status": "saved",
        "global_default_model": model_id,
        "path": str(MODEL_ASSIGN_PATH)
    }


def apply_model_to_all_tasks(model_id):
    schedule =YOUR_VALUE_HERE
    cfg =YOUR_VALUE_HERE

    cfg.setdefault("model_assignments", {})

    for task in schedule.get("tasks", []):
        task_id =YOUR_VALUE_HERE
        if task_id:
            cfg["model_assignments"][task_id] =YOUR_VALUE_HERE

    cfg["global_default_model"] =YOUR_VALUE_HERE

    save_json(MODEL_ASSIGN_PATH, cfg)

    return {
        "status": "saved",
        "model_id": model_id,
        "tasks_updated": len(schedule.get("tasks", [])),
        "path": str(MODEL_ASSIGN_PATH)
    }
