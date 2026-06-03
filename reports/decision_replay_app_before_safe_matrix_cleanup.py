import json
import subprocess
from pathlib import Path
from datetime import datetime

import streamlit as st

BASE = Path(__file__).resolve().parents[1]

REPLAY_PATH = BASE / "features" / "latest_decision_replay.json"
DECISION_STATUS_PATH = BASE / "features" / "latest_decision_data_status.json"
INTERPRETATION_PATH = BASE / "features" / "latest_decision_replay_interpretation.json"
PRICE_SNAPSHOT_PATH = BASE / "features" / "latest_price_snapshot.json"


st.set_page_config(
    page_title="Hermes Decision Replay",
    layout="wide"
)


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def run_cmd(cmd, timeout=180):
    try:
        r = subprocess.run(
            cmd,
            cwd=BASE,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {
            "status": "complete" if r.returncode == 0 else "error",
            "stdout": r.stdout[-1000:],
            "stderr": r.stderr[-1000:]
        }
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e)
        }

# ============================================================

def render_hermes_power_button():
    import subprocess as _hermes_power_subprocess

    st.markdown("""
    <style>
    /* Top-right-ish Hermes power control */
    div[data-testid="stHorizontalBlock"]:has(button[kind="secondary"]) {
        align-items: center;
    }

    .hermes-power-note {
        text-align: right;
        color: rgba(180,180,180,0.70);
        font-size: 0.78rem;
        margin-top: 0.48rem;
        margin-bottom: 0.20rem;
    }
    </style>
    """, unsafe_allow_html=True)

    _spacer, _power_col = st.columns([0.88, 0.12])

    with _power_col:
        if st.button("⏻ Shutdown", key="hermes_top_power_shutdown", type="secondary", use_container_width=True):
            _stop_script = BASE / "stop_hermes_apps.ps1"

            _hermes_power_subprocess.Popen(
                [
                    "powershell.exe",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(_stop_script)
                ],
                cwd=str(BASE)
            )

            st.warning("Shutdown requested. Hermes servers are stopping. Close browser tabs manually.")
            st.stop()

    st.markdown('<div class="hermes-power-note">Hermes app control</div>', unsafe_allow_html=True)

# ============================================================

def render_hermes_top_power_button():
    import subprocess as _hermes_shutdown_subprocess

    st.markdown("""
    <style>
    /* Fully hide Streamlit sidebar and sidebar collapse control */
    section[data-testid="stSidebar"] {
        display: none !important;
        width: 0 !important;
        min-width: 0 !important;
    }

    div[data-testid="collapsedControl"] {
        display: none !important;
    }

    /* Slightly reduce top padding so power button sits closer to top-right app area */
    section.main div.block-container {
        padding-top: 0.75rem !important;
    }

    /* Top power button row */
    .hermes-power-caption {
        text-align: right;
        color: rgba(180,180,180,0.72);
        font-size: 0.78rem;
        margin-top: 0.48rem;
        margin-bottom: 0.25rem;
    }
    </style>
    """, unsafe_allow_html=True)

    _left, _right = st.columns([0.86, 0.14])

    with _right:
        if st.button("⏻ Shutdown", key="hermes_top_power_shutdown_button", type="secondary", width="stretch"):
            _stop_script = BASE / "stop_hermes_apps.ps1"

            _hermes_shutdown_subprocess.Popen(
                [
                    "powershell.exe",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(_stop_script)
                ],
                cwd=str(BASE)
            )

            st.warning("Shutdown requested. Hermes servers are stopping. Close browser tabs manually.")
            st.stop()

    st.markdown('<div class="hermes-power-caption">Hermes app control</div>', unsafe_allow_html=True)

# ============================================================

def render_hermes_skinny_power_button():
    import subprocess as _hermes_shutdown_subprocess

    try:
        _shutdown_requested = st.query_params.get("hermes_shutdown", None)
    except Exception:
        _shutdown_requested = None

    if _shutdown_requested:
        _stop_script = BASE / "stop_hermes_apps.ps1"

        _hermes_shutdown_subprocess.Popen(
            [
                "powershell.exe",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(_stop_script)
            ],
            cwd=str(BASE)
        )

        st.warning("Shutdown requested. Hermes servers are stopping. Close browser tabs manually.")
        st.stop()

    st.markdown("""
    <style>
    /* Hide sidebar completely */
    section[data-testid="stSidebar"] {
        display: none !important;
        width: 0 !important;
        min-width: 0 !important;
        max-width: 0 !important;
    }

    div[data-testid="collapsedControl"] {
        display: none !important;
    }

    /* Tiny red fixed power button near Deploy */
    .hermes-skinny-power-button {
        position: fixed;
        top: 0.48rem;
        right: 7.10rem;
        z-index: 2147483647;
        width: 1.42rem;
        height: 1.22rem;
        border-radius: 999px;
        background: rgba(185, 28, 28, 0.92);
        border: 1px solid rgba(248, 113, 113, 0.88);
        color: rgba(255, 255, 255, 0.98) !important;
        display: flex;
        align-items: center;
        justify-content: center;
        text-decoration: none !important;
        font-size: 0.78rem;
        font-weight: 950;
        line-height: 1;
        box-shadow: 0 5px 14px rgba(0,0,0,0.35);
        backdrop-filter: blur(8px);
    }

    .hermes-skinny-power-button:hover {
        background: rgba(220, 38, 38, 0.98);
        border-color: rgba(252, 165, 165, 1.0);
        transform: translateY(-1px);
    }

    .hermes-skinny-power-button:active {
        background: rgba(127, 29, 29, 1.0);
        transform: translateY(0px);
    }
    </style>

    <a class="hermes-skinny-power-button" href="?hermes_shutdown=1" title="Shutdown Hermes Apps">⏻</a>
    """, unsafe_allow_html=True)

# ============================================================

def render_hermes_inline_power_button():
    import subprocess as _hermes_shutdown_subprocess

    try:
        _shutdown_requested = st.query_params.get("hermes_shutdown", None)
    except Exception:
        _shutdown_requested = None

    if _shutdown_requested:
        _stop_script = BASE / "stop_hermes_apps.ps1"

        _hermes_shutdown_subprocess.Popen(
            [
                "powershell.exe",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(_stop_script)
            ],
            cwd=str(BASE)
        )

        st.warning("Shutdown requested. Hermes servers are stopping. Close browser tabs manually.")
        st.stop()

    st.markdown("""
    <style>
    /* Hide Streamlit sidebar completely */
    section[data-testid="stSidebar"] {
        display: none !important;
        width: 0 !important;
        min-width: 0 !important;
        max-width: 0 !important;
    }

    div[data-testid="collapsedControl"] {
        display: none !important;
    }

    /* Top-right normal layout row, not floating */
    .hermes-inline-power-row {
        width: 100%;
        display: flex;
        justify-content: flex-end;
        align-items: center;
        margin-top: -0.35rem;
        margin-bottom: 0.55rem;
        padding-right: 0.15rem;
    }

    .hermes-inline-power-button {
        width: 2.15rem;
        height: 1.28rem;
        border-radius: 999px;
        background: rgba(185, 28, 28, 0.92);
        border: 1px solid rgba(248, 113, 113, 0.88);
        color: rgba(255, 255, 255, 0.98) !important;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        text-decoration: none !important;
        font-size: 0.82rem;
        font-weight: 950;
        line-height: 1;
        box-shadow: 0 4px 12px rgba(0,0,0,0.30);
    }

    .hermes-inline-power-button:hover {
        background: rgba(220, 38, 38, 0.98);
        border-color: rgba(252, 165, 165, 1.0);
        transform: translateY(-1px);
    }

    .hermes-inline-power-button:active {
        background: rgba(127, 29, 29, 1.0);
        transform: translateY(0px);
    }
    </style>

    <div class="hermes-inline-power-row">
        <a class="hermes-inline-power-button" href="?hermes_shutdown=1" title="Shutdown Hermes apps">⏻</a>
    </div>
    """, unsafe_allow_html=True)

# ============================================================

def render_hermes_app_control_menu():
    import subprocess as _hermes_shutdown_subprocess

    st.markdown("""
    <style>
    /* Hide Streamlit sidebar and top-left sidebar toggle */
    section[data-testid="stSidebar"] {
        display: none !important;
        width: 0 !important;
        min-width: 0 !important;
        max-width: 0 !important;
    }

    div[data-testid="collapsedControl"],
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapsedControl"],
    button[aria-label="Open sidebar"],
    button[title="Open sidebar"] {
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        height: 0 !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }

    /* Small right-aligned app-control row below Streamlit toolbar */
    .hermes-app-control-spacer {
        margin-top: -0.35rem;
        margin-bottom: 0.35rem;
    }

    /* Make popover trigger compact */
    div[data-testid="stPopover"] button {
        min-height: 1.80rem !important;
        height: 1.80rem !important;
        padding: 0.10rem 0.55rem !important;
        font-size: 0.78rem !important;
        border-radius: 999px !important;
        opacity: 0.88;
    }

    div[data-testid="stPopover"] button:hover {
        opacity: 1.0;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="hermes-app-control-spacer"></div>', unsafe_allow_html=True)

    _left, _right = st.columns([0.88, 0.12])

    with _right:
        with st.popover("⋮ App", use_container_width=True):
            st.caption("Hermes app control")

            if st.button("⏻ Shutdown Hermes Apps", key="hermes_menu_shutdown_all", type="secondary", use_container_width=True):
                _stop_script = BASE / "stop_hermes_apps.ps1"

                _hermes_shutdown_subprocess.Popen(
                    [
                        "powershell.exe",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        str(_stop_script)
                    ],
                    cwd=str(BASE)
                )

                st.warning("Shutdown requested. Hermes servers are stopping. Close browser tabs manually.")
                st.stop()

# ============================================================

def render_hermes_deploy_aligned_shutdown():
    import subprocess as _hermes_shutdown_subprocess

    try:
        _shutdown_requested = st.query_params.get("hermes_shutdown", None)
    except Exception:
        _shutdown_requested = None

    if _shutdown_requested:
        _stop_script = BASE / "stop_hermes_apps.ps1"

        _hermes_shutdown_subprocess.Popen(
            [
                "powershell.exe",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(_stop_script)
            ],
            cwd=str(BASE)
        )

        st.warning("Shutdown requested. Hermes servers are stopping. Close browser tabs manually.")
        st.stop()

    st.markdown("""
    <style>
    /* Hide Streamlit sidebar and top-left sidebar toggle */
    section[data-testid="stSidebar"] {
        display: none !important;
        width: 0 !important;
        min-width: 0 !important;
        max-width: 0 !important;
    }

    div[data-testid="collapsedControl"],
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapsedControl"],
    button[aria-label="Open sidebar"],
    button[title="Open sidebar"],
    button[aria-label="Close sidebar"],
    button[title="Close sidebar"] {
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        height: 0 !important;
        min-width: 0 !important;
        min-height: 0 !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }

    /* Normal app-layout row, aligned to right, just under Streamlit toolbar */
    .hermes-shutdown-row {
        width: 100%;
        display: flex;
        justify-content: flex-end;
        align-items: center;
        margin-top: -0.65rem;
        margin-bottom: 0.85rem;
        padding-right: 0.15rem;
    }

    .hermes-shutdown-mini {
        width: 2.05rem;
        height: 1.22rem;
        border-radius: 999px;
        background: rgba(185, 28, 28, 0.92);
        border: 1px solid rgba(248, 113, 113, 0.88);
        color: rgba(255, 255, 255, 0.98) !important;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        text-decoration: none !important;
        font-size: 0.78rem;
        font-weight: 950;
        line-height: 1;
        box-shadow: 0 4px 12px rgba(0,0,0,0.28);
    }

    .hermes-shutdown-mini:hover {
        background: rgba(220, 38, 38, 0.98);
        border-color: rgba(252, 165, 165, 1.0);
        transform: translateY(-1px);
    }

    .hermes-shutdown-mini:active {
        background: rgba(127, 29, 29, 1.0);
        transform: translateY(0px);
    }
    </style>

    <div class="hermes-shutdown-row">
        <a class="hermes-shutdown-mini" href="?hermes_shutdown=1" title="Shutdown Hermes Apps">⏻</a>
    </div>
    """, unsafe_allow_html=True)



# ============================================================
# Hermes Final Right-Edge Power Button
# ============================================================

def render_hermes_final_power_button():
    import subprocess as _hermes_shutdown_subprocess

    try:
        _shutdown_requested = st.query_params.get("hermes_shutdown", None)
    except Exception:
        _shutdown_requested = None

    if _shutdown_requested:
        _stop_script = BASE / "stop_hermes_apps.ps1"

        _hermes_shutdown_subprocess.Popen(
            [
                "powershell.exe",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(_stop_script)
            ],
            cwd=str(BASE)
        )

        st.warning("Shutdown requested. Hermes servers are stopping. Close browser tabs manually.")
        st.stop()

    st.markdown("""
    <style>
    /* Hide Streamlit sidebar and top-left sidebar toggle */
    section[data-testid="stSidebar"] {
        display: none !important;
        width: 0 !important;
        min-width: 0 !important;
        max-width: 0 !important;
    }

    div[data-testid="collapsedControl"],
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapsedControl"],
    button[aria-label="Open sidebar"],
    button[title="Open sidebar"],
    button[aria-label="Close sidebar"],
    button[title="Close sidebar"] {
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        height: 0 !important;
        min-width: 0 !important;
        min-height: 0 !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }

    /* Final button: small red circle below Deploy / 3-dot area */
    .hermes-final-power-button {
        position: fixed;
        top: 4.15rem;
        right: 1.05rem;
        z-index: 2147483647;

        width: 2.55rem;
        height: 2.55rem;
        border-radius: 999px;

        background: rgba(185, 28, 28, 0.94);
        border: 1px solid rgba(248, 113, 113, 0.95);
        color: rgba(255,255,255,0.98) !important;

        display: flex;
        align-items: center;
        justify-content: center;

        text-decoration: none !important;
        font-size: 1.18rem;
        font-weight: 950;
        line-height: 1;

        box-shadow: 0 7px 20px rgba(0,0,0,0.34);
        backdrop-filter: blur(8px);
    }

    .hermes-final-power-button:hover {
        background: rgba(220, 38, 38, 0.98);
        border-color: rgba(252, 165, 165, 1.0);
        transform: translateY(-1px);
    }

    .hermes-final-power-button:active {
        background: rgba(127, 29, 29, 1.0);
        transform: translateY(0px);
    }
    </style>

    <a class="hermes-final-power-button" href="?hermes_shutdown=1" title="Shutdown Hermes Apps">⏻</a>
    """, unsafe_allow_html=True)


render_hermes_final_power_button()

st.title("Hermes Decision Replay")
st.caption("Replay readiness for manual actions, agent suggestions, thesis records, and portfolio snapshots. Advisory only.")

if st.button("Refresh Decision Data + Replay", width="stretch"):
    r0 = run_cmd(["py", "tools\\price_fallback_engine.py"])
    r1 = run_cmd(["py", "tools\\decision_data_engine.py"])
    r2 = run_cmd(["py", "tools\\decision_replay_engine.py"])
    r3 = run_cmd(["py", "tools\\decision_replay_interpreter.py"])
    st.toast(f"Prices: {r0.get('status')} | Data: {r1.get('status')} | Replay: {r2.get('status')} | Interpretation: {r3.get('status')}")
    st.rerun()

replay = load_json(REPLAY_PATH, {})
decision = load_json(DECISION_STATUS_PATH, {})
interpretation_packet = load_json(INTERPRETATION_PATH, {})
price_snapshot = load_json(PRICE_SNAPSHOT_PATH, {})

summary = replay.get("summary", {})
counts = replay.get("counts", {})

st.markdown("## Replay Summary")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Replay Status", summary.get("overall_status", "unknown"))
c2.metric("Manual Ready", summary.get("manual_ready_count", 0))
c3.metric("Agent Ready", summary.get("agent_ready_count", 0))
c4.metric("Portfolio Positions", counts.get("portfolio_positions", 0))

st.info(summary.get("read", "Replay engine has not run yet."))

missing_prices = replay.get("tickers_missing_current_price", [])

if missing_prices:
    st.markdown("### Missing Current Price")
    for ticker in missing_prices:
        st.markdown(f"- 🔴 {ticker}")
else:
    st.success("No tickers are missing current price.")


st.markdown("---")
st.markdown("## Replay Interpretation")

interpretation = interpretation_packet.get("interpretation", {})

headline = interpretation.get("headline", "Decision replay interpretation has not run yet.")
severity = interpretation.get("severity", "yellow")
plain_read = interpretation.get("plain_english_read", "Run the replay interpreter to generate an interpretation.")
positives = interpretation.get("positives", [])
blockers = interpretation.get("blockers", [])
next_actions = interpretation.get("next_actions", [])
metrics = interpretation.get("metrics", {})

if severity == "green":
    st.success(headline)
elif severity == "red":
    st.error(headline)
else:
    st.warning(headline)

st.info(plain_read)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Manual Actions", metrics.get("manual_actions", 0))
m2.metric("Manual Ready", metrics.get("manual_ready", 0))
m3.metric("Agent Ready", metrics.get("agent_ready", 0))
m4.metric("Missing Prices", metrics.get("missing_current_price_count", 0))

left_col, right_col = st.columns(2)

with left_col:
    st.markdown("### Positives")
    if positives:
        for item in positives:
            st.markdown(f"- ✅ {item}")
    else:
        st.caption("No positives yet.")

    st.markdown("### Blockers")
    if blockers:
        for item in blockers:
            st.markdown(f"- 🔴 {item}")
    else:
        st.success("No blockers detected.")

with right_col:
    st.markdown("### Next Actions")
    if next_actions:
        for item in next_actions:
            st.markdown(f"- {item}")
    else:
        st.caption("No next actions generated.")


st.markdown("---")



# ============================================================
# Compact Replay Matrix
# ============================================================

st.markdown("""
<style>

/* Extra compact replay matrix */
div[data-testid="stDataFrame"] {
    width: 100% !important;
}

div[data-testid="stDataFrame"] [role="gridcell"],
div[data-testid="stDataFrame"] [role="columnheader"] {
    padding-top: 0.25rem !important;
    padding-bottom: 0.25rem !important;
}

/* Tighter replay tables */
[data-testid="stDataFrame"] {
    font-size: 0.86rem !important;
}

div[data-testid="stDataFrame"] div {
    line-height: 1.15rem !important;
}

.compact-replay-note {
    color: rgba(210,210,210,0.72);
    font-size: 0.88rem;
    margin-bottom: 0.35rem;
}
</style>
""", unsafe_allow_html=True)


def fmt_price(value):
    try:
        if value is None or value == "":
            return ""
        return f"{float(value):.2f}"
    except Exception:
        return ""


def fmt_pct(value):
    try:
        if value is None or value == "":
            return ""
        return f"{float(value):+.2f}%"
    except Exception:
        return ""




def fmt_simple_date(value):
    if not value:
        return ""

    raw = str(value)

    try:
        cleaned = raw.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        return dt.strftime("%b %d")
    except Exception:
        pass

    # Fallback for ISO-like strings.
    if "T" in raw:
        raw = raw.split("T")[0]

    parts = raw.split("-")
    if len(parts) == 3:
        try:
            dt = datetime(int(parts[0]), int(parts[1]), int(parts[2]))
            return dt.strftime("%b %d")
        except Exception:
            return raw

    return raw[:10]


def latest_by_ticker(rows):
    latest = {}
    for row in rows:
        ticker = str(row.get("ticker", "")).upper()
        if ticker:
            latest[ticker] = row
    return latest


def suggestion_icon(value):
    value = str(value or "").lower()

    if value == "wait_for_confirmation":
        return "⏳ Wait"
    if "monitor" in value:
        return "👀 Watch"
    if "upgrade" in value:
        return "⬆️ Upgrade"
    if "downgrade" in value:
        return "⬇️ Downgrade"
    if value == "avoid":
        return "⛔ Avoid"
    if value == "watch":
        return "👀 Watch"

    return value.replace("_", " ") if value else ""


def readiness_icon(value):
    return "✅" if value else "❌"


def price_verified_icon(item):
    if not item:
        return "❔"

    status = str(item.get("status", "")).lower()
    verified = bool(item.get("verified", False))

    if verified or status in ["verified_external", "verified external", "verified_external_manual_disagreement"]:
        return "✅"
    if "single" in status:
        return "⚠️"
    if "disagreement" in status or "missing" in status or "no_external" in status:
        return "❌"

    return "❔"


def price_status_short(item):
    if not item:
        return "No check"

    status = str(item.get("status", "")).replace("_", " ")

    if status == "verified external":
        return "✅ Verified"
    if status == "verified external manual disagreement":
        return "✅ External verified"
    if "single" in status:
        return "⚠️ One source"
    if "disagreement" in status:
        return "❌ Disagree"
    if "missing" in status or "no external" in status:
        return "❌ Missing"

    return status


def clean_status(row, kind):
    if not row:
        return "No record"

    if row.get("replay_ready"):
        move = row.get("movement_pct")
        try:
            move_val = float(move)
            if move_val > 0:
                return "✅ Higher"
            if move_val < 0:
                return "✅ Lower"
            return "✅ Flat"
        except Exception:
            return "✅ Ready"

    missing = row.get("missing", [])
    if "current_price" in missing:
        return "❌ Needs current"
    if "action_price" in missing or "reference_price" in missing:
        return "❌ Needs ref"

    return "❌ Blocked"


def next_action_for(manual, agent, price_item):
    if price_item:
        status = str(price_item.get("status", "")).lower()
        if "disagreement" in status:
            return "Review price"
        if "single" in status:
            return "Confirm price"
        if price_item.get("verified"):
            pass
        elif "missing" in status or "no_external" in status:
            return "Add price"

    if manual and not manual.get("replay_ready"):
        return "Fix manual ref/current"
    if agent and not agent.get("replay_ready"):
        return "Fix agent ref/current"

    if manual and agent:
        return "Monitor result"
    if manual and not agent:
        return "Log agent idea"
    if agent and not manual:
        return "Log manual action"

    return "No action"


def build_price_map(price_snapshot):
    out = {}
    for item in price_snapshot.get("results", []):
        ticker = str(item.get("ticker", "")).upper()
        if ticker:
            out[ticker] = item
    return out


def build_replay_matrix(replay, price_snapshot):
    manual_map = latest_by_ticker(replay.get("manual_replays", []))
    agent_map = latest_by_ticker(replay.get("agent_replays", []))
    thesis_map = replay.get("latest_thesis_by_ticker", {})
    price_map = build_price_map(price_snapshot)

    tickers = sorted(set(list(manual_map.keys()) + list(agent_map.keys()) + list(thesis_map.keys()) + list(price_map.keys())))

    rows = []

    for ticker in tickers:
        manual = manual_map.get(ticker)
        agent = agent_map.get(ticker)
        thesis = thesis_map.get(ticker, {})
        price_item = price_map.get(ticker)

        current_price = ""
        if price_item and price_item.get("selected_price"):
            current_price = fmt_price(price_item.get("selected_price"))
        elif manual:
            current_price = fmt_price(manual.get("current_price"))
        elif agent:
            current_price = fmt_price(agent.get("current_price"))

        manual_ref = fmt_price(manual.get("action_price")) if manual else ""
        agent_ref = fmt_price(agent.get("reference_price")) if agent else ""

        signal = suggestion_icon(agent.get("suggestion_type")) if agent else ""
        move_value = fmt_pct(manual.get("movement_pct")) if manual else fmt_pct(agent.get("movement_pct")) if agent else ""

        ref_value = manual_ref if manual_ref else agent_ref

        thesis_status = str(thesis.get("thesis_status", "")).replace("_", " ") if thesis else ""
        if thesis_status == "intact":
            thesis_short = "✅ Intact"
        elif thesis_status == "invalidated":
            thesis_short = "❌ Invalid"
        elif thesis_status == "weakening":
            thesis_short = "⚠️ Weak"
        elif thesis_status:
            thesis_short = "⚠️ Review"
        else:
            thesis_short = "—"

        exp_move = thesis.get("expected_move_pct", "") if thesis else ""
        stop_loss = thesis.get("stop_loss", "") if thesis else ""

        agent_model = ""
        if agent:
            agent_name = agent.get("agent", "")
            model_name = agent.get("model", "")
            if agent_name and model_name:
                agent_model = f"{agent_name} / {model_name}"
            elif agent_name:
                agent_model = agent_name
            elif model_name:
                agent_model = model_name

        replay_timestamp = ""
        if manual and manual.get("timestamp"):
            replay_timestamp = manual.get("timestamp")
        elif agent and agent.get("timestamp"):
            replay_timestamp = agent.get("timestamp")
        elif thesis and thesis.get("timestamp"):
            replay_timestamp = thesis.get("timestamp")

        replay_date = fmt_simple_date(replay_timestamp)

        rows.append({
            "Ticker": ticker,
            "Date": replay_date,
            "M": readiness_icon(manual.get("replay_ready")) if manual else "—",
            "A": readiness_icon(agent.get("replay_ready")) if agent else "—",
            "P": price_verified_icon(price_item),
            "Thesis": thesis_short,
            "Signal": signal,
            "Agent": agent_model,
            "Ref": ref_value,
            "Now": current_price,
            "Move": move_value,
            "Exp": exp_move,
            "Stop": stop_loss,
            "Price": price_status_short(price_item),
            "Next": next_action_for(manual, agent, price_item)
        })

    return rows


def build_action_needed(replay, price_snapshot):
    rows = []

    for ticker in replay.get("tickers_missing_current_price", []):
        rows.append({
            "Ticker": ticker,
            "Issue": "❌ Missing current price",
            "Next": "Update current price."
        })

    for item in price_snapshot.get("results", []):
        ticker = item.get("ticker", "")
        status = str(item.get("status", "")).lower()

        if "disagreement" in status:
            rows.append({
                "Ticker": ticker,
                "Issue": "❌ Price disagreement",
                "Next": "Review manual price vs external sources."
            })
        elif "single" in status:
            rows.append({
                "Ticker": ticker,
                "Issue": "⚠️ One price source",
                "Next": "Confirm with another source."
            })
        elif "missing" in status or "no_external" in status:
            rows.append({
                "Ticker": ticker,
                "Issue": "❌ No external price",
                "Next": "Refresh or add price source."
            })

    # Deduplicate
    seen = set()
    clean = []
    for row in rows:
        key = (row.get("Ticker"), row.get("Issue"))
        if key not in seen:
            seen.add(key)
            clean.append(row)

    return clean


tab_matrix, tab_actions = st.tabs([
    "Replay Matrix",
    "Action Needed"
])

with tab_matrix:
    st.markdown("## Replay Matrix")
    st.caption("Compact replay view. Icons replace backend fields: manual ready, agent ready, price verification, thesis status, and next action.")

    rows = build_replay_matrix(replay, price_snapshot)

    if rows:
        st.dataframe(
            rows,
            width="stretch",
            hide_index=True,
            column_config={
                "Ticker": st.column_config.TextColumn(
                    "Ticker",
                    help="Stock ticker being evaluated in replay."
                ),
                "Date": st.column_config.TextColumn(
                    "Date",
                    help="Simplified date of the latest replay-related record for this ticker."
                ),
                "M": st.column_config.TextColumn(
                    "M",
                    help="Manual replay status. ✅ means latest manual action has usable reference and current price. ❌ means blocked. — means no manual record."
                ),
                "A": st.column_config.TextColumn(
                    "A",
                    help="Agent replay status. ✅ means latest agent suggestion can be replayed. ❌ means blocked. — means no agent record."
                ),
                "P": st.column_config.TextColumn(
                    "P",
                    help="Price verification. ✅ means externally verified. ⚠️ means needs review. ❌ means missing/disagreement."
                ),
                "T": st.column_config.TextColumn(
                    "T",
                    help="Thesis status. ✅ means a thesis health record exists. — means no thesis record yet."
                ),
                "Signal": st.column_config.TextColumn(
                    "Signal",
                    help="Agent suggestion signal. ⏳ Wait means wait for confirmation. 👀 Watch means monitor. ⬆️/⬇️ means conviction change."
                ),
                "Ref": st.column_config.TextColumn(
                    "Ref",
                    help="Reference/action price used to measure replay performance."
                ),
                "Now": st.column_config.TextColumn(
                    "Now",
                    help="Current price used for replay. Should come from verified or reviewed price data."
                ),
                "Move": st.column_config.TextColumn(
                    "Move",
                    help="Percent move from reference price to current price."
                ),
                "Price": st.column_config.TextColumn(
                    "Price",
                    help="Plain-language price verification status."
                ),
                "Next": st.column_config.TextColumn(
                    "Next",
                    help="Suggested next action based on replay readiness and price verification."
                ),
            }
        )
    else:
        st.warning("No replay records available yet.")


with tab_actions:
    st.markdown("## Action Needed")
    st.caption("Only items that need attention before replay is reliable.")

    rows = build_action_needed(replay, price_snapshot)

    if rows:
        st.dataframe(rows, width="stretch", hide_index=True)
    else:
        st.success("No replay blockers detected.")

