
import json
import subprocess
import webbrowser
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]
CONFIG = BASE / "config" / "browser_source_config.json"
REGISTRY = BASE / "logs" / "research_browser_processes.json"

WINDOWS_BROWSER_PATHS = {
    "chrome": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    ],
    "edge": [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    ],
    "chromium": [
        r"C:\Program Files\Chromium\Application\chrome.exe",
        r"C:\Program Files (x86)\Chromium\Application\chrome.exe",
        r"C:\Users\Abe\AppData\Local\Chromium\Application\chrome.exe"
    ]
}

BLOCKED_ACTIONS = [
    "buy",
    "sell",
    "trade",
    "place_order",
    "post",
    "comment",
    "reply",
    "like",
    "message",
    "follow",
    "change_account_settings"
]

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default

def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def load_config():
    return load_json(CONFIG, {})

def get_source(source_id):
    cfg = load_config()
    for src in cfg.get("sources", []):
        if src.get("id") == source_id:
            return src
    return None

def list_sources():
    cfg = load_config()
    return [
        {
            "id": s.get("id"),
            "label": s.get("label"),
            "url": s.get("url"),
            "source_type": s.get("source_type"),
            "requires_login": s.get("requires_login")
        }
        for s in cfg.get("sources", [])
    ]

def find_browser_exe(browser_name):
    for p in WINDOWS_BROWSER_PATHS.get(browser_name, []):
        if Path(p).exists():
            return p
    return None

def pick_browser():
    cfg = load_config()
    sel = cfg.get("browser_selection", {})

    order = [
        sel.get("preferred_browser", "chromium"),
        sel.get("fallback_browser", "chrome"),
        sel.get("second_fallback_browser", "edge")
    ]

    for name in order:
        exe = find_browser_exe(name)
        if exe:
            return name, exe

    return "default", None

def get_profile_path():
    cfg = load_config()
    sel = cfg.get("browser_selection", {})
    profile_path = Path(sel.get("browser_profile_path", BASE / "data" / "browser_profiles" / "hermes_research"))
    profile_path.mkdir(parents=True, exist_ok=True)
    return profile_path

def register_process(pid, browser_name, source_id, url, profile_path):
    data = load_json(REGISTRY, {"processes": []})
    data.setdefault("processes", [])
    data["processes"].append({
        "pid": pid,
        "browser": browser_name,
        "source_id": source_id,
        "url": url,
        "profile": str(profile_path),
        "started_at": utc_now()
    })
    save_json(REGISTRY, data)

def open_source(source_id):
    src = get_source(source_id)

    if not src:
        return {
            "status": "error",
            "error": f"unknown_source:{source_id}"
        }

    url = src.get("url")
    profile_path = get_profile_path()
    browser_name, exe = pick_browser()

    if exe:
        cmd = [
            exe,
            f"--user-data-dir={profile_path}",
            "--new-window",
            "--no-first-run",
            "--disable-popup-blocking",
            url
        ]

        proc = subprocess.Popen(cmd)
        register_process(proc.pid, browser_name, source_id, url, profile_path)

        return {
            "status": "opened",
            "source_id": source_id,
            "url": url,
            "browser": browser_name,
            "pid": proc.pid,
            "profile": str(profile_path),
            "policy": "view_only",
            "blocked_actions": BLOCKED_ACTIONS
        }

    webbrowser.open(url)

    return {
        "status": "opened_default_browser",
        "source_id": source_id,
        "url": url,
        "browser": "default",
        "profile": "default",
        "policy": "view_only",
        "blocked_actions": BLOCKED_ACTIONS
    }

def close_registered_browsers():
    data = load_json(REGISTRY, {"processes": []})
    processes = data.get("processes", [])

    closed = []
    failed = []

    for item in processes:
        pid = item.get("pid")
        if not pid:
            continue

        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                text=True,
                timeout=15
            )
            closed.append(item)
        except Exception as e:
            item["close_error"] = str(e)
            failed.append(item)

    save_json(REGISTRY, {
        "processes": [],
        "last_closed_at": utc_now(),
        "closed_count": len(closed),
        "failed_count": len(failed)
    })

    return {
        "status": "complete",
        "closed_count": len(closed),
        "failed_count": len(failed),
        "closed": closed,
        "failed": failed
    }

def browser_status():
    return load_json(REGISTRY, {"processes": []})

if __name__ == "__main__":
    import sys

    if "--close" in sys.argv:
        print(json.dumps(close_registered_browsers(), indent=2))
    elif "--status" in sys.argv:
        print(json.dumps(browser_status(), indent=2))
    elif len(sys.argv) > 1:
        print(json.dumps(open_source(sys.argv[1]), indent=2))
    else:
        print(json.dumps({
            "browser": pick_browser()[0],
            "profile": str(get_profile_path()),
            "sources": list_sources()
        }, indent=2))
