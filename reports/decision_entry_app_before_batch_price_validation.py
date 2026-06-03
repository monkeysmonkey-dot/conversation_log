import json
from pathlib import Path
from datetime import datetime, timezone

import streamlit as st
import pandas as pd

BASE = Path(__file__).resolve().parents[1]

MANUAL_ACTIONS = BASE / "data" / "manual_actions_journal.jsonl"
AGENT_SUGGESTIONS = BASE / "data" / "agent_suggestions_journal.jsonl"
THESIS_HEALTH = BASE / "data" / "thesis_health_journal.jsonl"
PORTFOLIO_SNAPSHOT = BASE / "data" / "portfolio_snapshot.json"
DECISION_STATUS = BASE / "features" / "latest_decision_data_status.json"
BATCH_REPLAY_CSV = BASE / "data" / "replay_price_updates.csv"
DECISION_REPLAY = BASE / "features" / "latest_decision_replay.json"


st.set_page_config(
    page_title="Hermes Decision Entry",
    layout="wide"
)


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def append_jsonl(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def split_tags(raw):
    if not raw:
        return []
    return [x.strip() for x in str(raw).split(",") if x.strip()]


def run_decision_engine():
    import subprocess
    try:
        r = subprocess.run(
            ["py", "tools\\decision_data_engine.py"],
            cwd=BASE,
            capture_output=True,
            text=True,
            timeout=180
        )
        return {
            "status": "complete" if r.returncode == 0 else "error",
            "returncode": r.returncode,
            "stdout": r.stdout[-1000:],
            "stderr": r.stderr[-1000:]
        }
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e)
        }



def replay_missing_current_prices():
    replay = load_json(DECISION_REPLAY, {})
    tickers = replay.get("tickers_missing_current_price", [])
    if not isinstance(tickers, list):
        return []
    return [str(x).upper() for x in tickers if x]


def decision_status():
    return load_json(DECISION_STATUS, {
        "overall_status": "data_missing",
        "read": "Decision data engine has not run yet.",
        "missing": [],
        "counts": {
            "manual_actions": 0,
            "agent_suggestions": 0,
            "thesis_records": 0,
            "portfolio_snapshot_present": False
        }
    })

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

st.title("Hermes Decision Entry")
st.caption("Manual decision journal. Advisory only. This does not execute trades.")

status = decision_status()
counts = status.get("counts", {})

c1, c2, c3, c4 = st.columns(4)
c1.metric("Decision Status", status.get("overall_status", "data_missing"))
c2.metric("Manual Actions", counts.get("manual_actions", 0))
c3.metric("Agent Suggestions", counts.get("agent_suggestions", 0))
c4.metric("Thesis Records", counts.get("thesis_records", 0))

st.info(status.get("read", "Decision data engine has not run yet."))

if st.button("Refresh Decision Data Status", width="stretch"):
    result = run_decision_engine()
    st.toast(f"Decision data refresh: {result.get('status')}")
    st.rerun()


st.markdown("---")
st.markdown("## Replay Missing Current Prices")
st.caption("Use this to quickly fill the current price needed by Decision Replay.")

missing_price_tickers = replay_missing_current_prices()

if missing_price_tickers:
    q1, q2, q3 = st.columns([1, 1, 2])

    with q1:
        quick_ticker = st.selectbox("Ticker needing current price", missing_price_tickers)

    with q2:
        quick_price = st.number_input("Current price", value=0.0, key="quick_missing_current_price")

    with q3:
        quick_notes = st.text_input("Notes", value="Quick replay current price update")

    if st.button("Save Current Price For Replay", width="stretch"):
        current = load_json(PORTFOLIO_SNAPSHOT, {})
        current.setdefault("positions", {})

        current["positions"][quick_ticker.upper()] = {
            "ticker": quick_ticker.upper(),
            "quantity": 0,
            "average_cost": 0,
            "current_price": quick_price,
            "market_value": 0,
            "unrealized_pnl": 0,
            "notes": quick_notes,
            "updated_at": now_utc(),
            "advisory_only": True
        }

        current["updated_at"] = now_utc()
        current["source"] = "decision_entry_quick_missing_price"
        current["advisory_only"] = True

        save_json(PORTFOLIO_SNAPSHOT, current)
        run_decision_engine()

        # Also refresh replay and interpretation if available.
        import subprocess
        try:
            subprocess.run(["py", "tools\\decision_replay_engine.py"], cwd=BASE, capture_output=True, text=True, timeout=180)
            subprocess.run(["py", "tools\\decision_replay_interpreter.py"], cwd=BASE, capture_output=True, text=True, timeout=180)
        except Exception:
            pass

        st.success(f"Saved current price for {quick_ticker.upper()}. Replay data refreshed.")
        st.rerun()
else:
    st.success("No tickers are currently missing current price for replay.")


st.markdown("---")

tab_manual, tab_agent, tab_thesis, tab_batch, tab_portfolio = st.tabs([
    "Log Manual Action",
    "Log Agent Suggestion",
    "Update Thesis Health",
    "Batch Replay Updates",
    "Portfolio Snapshot"
])


with tab_manual:
    st.markdown("## Log Manual Action")
    st.caption("Use this for your own actions: watch, wait, buy, sell, trim, add, avoid, conviction changes.")

    with st.form("manual_action_form", clear_on_submit=True):
        ticker = st.text_input("Ticker", value="AAPL")
        action_type = st.selectbox(
            "Action Type",
            [
                "watch",
                "wait",
                "buy",
                "sell",
                "trim",
                "add",
                "hold",
                "avoid",
                "upgrade_conviction",
                "downgrade_conviction",
                "remove_watchlist"
            ]
        )

        col1, col2 = st.columns(2)
        with col1:
            price = st.number_input("Reference / action price", value=0.0)
        with col2:
            quantity = st.number_input("Quantity", value=0.0)

        reason = st.text_area("Reason", value="Logged from Decision Entry app.")
        notes = st.text_area("Notes", value="")
        tags = st.text_input("Tags, comma separated", value="manual")

        submitted = st.form_submit_button("Save Manual Action", use_container_width=True)

        if submitted:
            row = {
                "timestamp": now_utc(),
                "ticker": ticker.upper(),
                "action_type": action_type,
                "price": price,
                "quantity": quantity,
                "reason": reason,
                "notes": notes,
                "tags": split_tags(tags),
                "source": "decision_entry_app",
                "advisory_only": True
            }
            append_jsonl(MANUAL_ACTIONS, row)
            run_decision_engine()
            st.success(f"Manual action saved for {ticker.upper()}")


with tab_agent:
    st.markdown("## Log Agent Suggestion")
    st.caption("Use this for what the system/agent suggested, not what you necessarily did.")

    with st.form("agent_suggestion_form", clear_on_submit=True):
        ticker = st.text_input("Ticker", value="AAPL", key="agent_ticker")
        suggestion_type = st.selectbox(
            "Suggestion Type",
            [
                "watch",
                "wait_for_confirmation",
                "upgrade_conviction",
                "downgrade_conviction",
                "avoid",
                "review_after_event_window",
                "monitor_volume",
                "monitor_relative_strength",
                "monitor_filing_or_insider",
                "monitor_macro_confirmation"
            ]
        )

        col1, col2 = st.columns(2)
        with col1:
            reference_price = st.number_input("Reference price", value=0.0)
        with col2:
            confidence = st.text_input("Confidence", value="medium")

        agent = st.text_input("Agent", value="dashboard")
        model = st.text_input("Model", value="")
        reason = st.text_area("Reason", value="Agent suggestion logged manually.")
        notes = st.text_area("Notes", value="", key="agent_notes")
        tags = st.text_input("Tags, comma separated", value="agent")

        submitted = st.form_submit_button("Save Agent Suggestion", use_container_width=True)

        if submitted:
            row = {
                "timestamp": now_utc(),
                "ticker": ticker.upper(),
                "suggestion_type": suggestion_type,
                "reference_price": reference_price,
                "confidence": confidence,
                "agent": agent,
                "model": model,
                "reason": reason,
                "notes": notes,
                "tags": split_tags(tags),
                "source": "decision_entry_app",
                "advisory_only": True
            }
            append_jsonl(AGENT_SUGGESTIONS, row)
            run_decision_engine()
            st.success(f"Agent suggestion saved for {ticker.upper()}")


with tab_thesis:
    st.markdown("## Update Thesis Health")
    st.caption("Track whether the original thesis is intact, strengthening, weakening, or invalidated.")

    with st.form("thesis_health_form", clear_on_submit=True):
        ticker = st.text_input("Ticker", value="AAPL", key="thesis_ticker")
        thesis_status = st.selectbox(
            "Thesis Status",
            [
                "new",
                "intact",
                "strengthening",
                "weakening",
                "needs_review",
                "invalidated",
                "closed"
            ]
        )
        conviction = st.selectbox("Conviction", ["low", "medium", "high", "unknown"])
        supporting_evidence = st.text_area("Supporting Evidence", value="")
        invalidating_evidence = st.text_area("Invalidating Evidence", value="")
        notes = st.text_area("Notes", value="", key="thesis_notes")
        tags = st.text_input("Tags, comma separated", value="thesis")

        submitted = st.form_submit_button("Save Thesis Health", use_container_width=True)

        if submitted:
            row = {
                "timestamp": now_utc(),
                "ticker": ticker.upper(),
                "thesis_status": thesis_status,
                "conviction": conviction,
                "supporting_evidence": supporting_evidence,
                "invalidating_evidence": invalidating_evidence,
                "notes": notes,
                "tags": split_tags(tags),
                "source": "decision_entry_app",
                "advisory_only": True
            }
            append_jsonl(THESIS_HEALTH, row)
            run_decision_engine()
            st.success(f"Thesis health saved for {ticker.upper()}")


with tab_batch:
    st.markdown("## Batch Replay Updates")
    st.caption("Update current prices and optionally log replay-ready manual actions, agent suggestions, and thesis records for multiple tickers.")

    default_rows = [
        {
            "ticker": "AAPL",
            "current_price": 0.0,
            "reference_price": 0.0,
            "log_manual": True,
            "log_agent": True,
            "log_thesis": True,
            "notes": "Batch replay update"
        }
    ]

    if not BATCH_REPLAY_CSV.exists():
        BATCH_REPLAY_CSV.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(default_rows).to_csv(BATCH_REPLAY_CSV, index=False)

    try:
        batch_df = pd.read_csv(BATCH_REPLAY_CSV)
    except Exception:
        batch_df = pd.DataFrame(default_rows)

    required_cols = ["ticker", "current_price", "reference_price", "log_manual", "log_agent", "log_thesis", "notes"]
    for col in required_cols:
        if col not in batch_df.columns:
            if col in ["log_manual", "log_agent", "log_thesis"]:
                batch_df[col] = True
            elif col in ["current_price", "reference_price"]:
                batch_df[col] = 0.0
            else:
                batch_df[col] = ""

    st.markdown("### Editable Batch Table")
    edited_df = st.data_editor(
        batch_df[required_cols],
        width="stretch",
        hide_index=True,
        num_rows="dynamic",
        key="batch_replay_update_editor"
    )

    b1, b2, b3 = st.columns(3)

    with b1:
        if st.button("Save Batch Table", width="stretch"):
            edited_df.to_csv(BATCH_REPLAY_CSV, index=False)
            st.success(f"Saved batch table to {BATCH_REPLAY_CSV}")

    with b2:
        if st.button("Reload Batch Table", width="stretch"):
            st.rerun()

    with b3:
        if st.button("Run Batch Replay Update", width="stretch"):
            edited_df.to_csv(BATCH_REPLAY_CSV, index=False)

            updated = []
            skipped = []

            current = load_json(PORTFOLIO_SNAPSHOT, {})
            current.setdefault("positions", {})

            for _, row in edited_df.iterrows():
                ticker = str(row.get("ticker", "")).strip().upper()

                try:
                    current_price = float(row.get("current_price", 0) or 0)
                except Exception:
                    current_price = 0.0

                try:
                    reference_price = float(row.get("reference_price", 0) or 0)
                except Exception:
                    reference_price = 0.0

                log_manual = bool(row.get("log_manual", False))
                log_agent = bool(row.get("log_agent", False))
                log_thesis = bool(row.get("log_thesis", False))
                notes = str(row.get("notes", ""))

                if not ticker:
                    skipped.append({"ticker": ticker, "reason": "missing ticker"})
                    continue

                if current_price <= 0:
                    skipped.append({"ticker": ticker, "reason": "current price must be greater than zero"})
                    continue

                old = current["positions"].get(ticker, {})

                current["positions"][ticker] = {
                    "ticker": ticker,
                    "quantity": old.get("quantity", 0),
                    "average_cost": old.get("average_cost", 0),
                    "current_price": current_price,
                    "market_value": old.get("market_value", 0),
                    "unrealized_pnl": old.get("unrealized_pnl", 0),
                    "notes": notes or "Batch replay current price update",
                    "updated_at": now_utc(),
                    "advisory_only": True
                }

                actions = ["portfolio_current_price_updated"]

                if reference_price > 0 and log_manual:
                    append_jsonl(MANUAL_ACTIONS, {
                        "timestamp": now_utc(),
                        "ticker": ticker,
                        "action_type": "watch",
                        "price": reference_price,
                        "quantity": 0,
                        "reason": "Batch replay-ready watch record",
                        "notes": notes,
                        "tags": ["batch", "replay"],
                        "source": "decision_entry_batch_replay",
                        "advisory_only": True
                    })
                    actions.append("manual_logged")

                if reference_price > 0 and log_agent:
                    append_jsonl(AGENT_SUGGESTIONS, {
                        "timestamp": now_utc(),
                        "ticker": ticker,
                        "suggestion_type": "wait_for_confirmation",
                        "reference_price": reference_price,
                        "confidence": "medium",
                        "agent": "decision_entry_batch_replay",
                        "model": "manual_input",
                        "reason": "Batch replay-ready agent suggestion",
                        "notes": notes,
                        "tags": ["batch", "agent", "replay"],
                        "source": "decision_entry_batch_replay",
                        "advisory_only": True
                    })
                    actions.append("agent_logged")

                if log_thesis:
                    append_jsonl(THESIS_HEALTH, {
                        "timestamp": now_utc(),
                        "ticker": ticker,
                        "thesis_status": "needs_review",
                        "conviction": "medium",
                        "supporting_evidence": "Ticker is active in replay workflow.",
                        "invalidating_evidence": "Needs confirmation from volume, relative strength, macro, and narrative.",
                        "notes": notes,
                        "tags": ["batch", "thesis", "replay"],
                        "source": "decision_entry_batch_replay",
                        "advisory_only": True
                    })
                    actions.append("thesis_logged")

                updated.append({
                    "ticker": ticker,
                    "current_price": current_price,
                    "reference_price": reference_price,
                    "actions": actions
                })

            current["updated_at"] = now_utc()
            current["source"] = "decision_entry_batch_replay"
            current["advisory_only"] = True
            save_json(PORTFOLIO_SNAPSHOT, current)

            result = run_decision_engine()

            import subprocess
            try:
                subprocess.run(["py", "tools\\decision_replay_engine.py"], cwd=BASE, capture_output=True, text=True, timeout=180)
                subprocess.run(["py", "tools\\decision_replay_interpreter.py"], cwd=BASE, capture_output=True, text=True, timeout=180)
            except Exception as e:
                st.warning(f"Replay refresh warning: {e}")

            st.session_state["batch_replay_last_result"] = {
                "updated": updated,
                "skipped": skipped
            }

            st.success(f"Batch update complete. Updated: {len(updated)} | Skipped: {len(skipped)}")

    batch_result = st.session_state.get("batch_replay_last_result", None)

    if batch_result:
        updated = batch_result.get("updated", [])
        skipped = batch_result.get("skipped", [])

        st.markdown("---")
        st.markdown("## Batch Update Result")

        r1, r2 = st.columns(2)
        r1.metric("Updated", len(updated))
        r2.metric("Skipped", len(skipped))

        if updated:
            st.markdown("### Updated Tickers")

            updated_rows = []
            for item in updated:
                updated_rows.append({
                    "Ticker": item.get("ticker"),
                    "Current Price": item.get("current_price"),
                    "Reference Price": item.get("reference_price"),
                    "Portfolio": "updated" if "portfolio_current_price_updated" in item.get("actions", []) else "",
                    "Manual": "logged" if "manual_logged" in item.get("actions", []) else "",
                    "Agent": "logged" if "agent_logged" in item.get("actions", []) else "",
                    "Thesis": "logged" if "thesis_logged" in item.get("actions", []) else ""
                })

            st.dataframe(updated_rows, width="stretch", hide_index=True)

        if skipped:
            st.warning(f"Skipped {len(skipped)} row(s).")

            skipped_rows = []
            for item in skipped:
                skipped_rows.append({
                    "Ticker": item.get("ticker", ""),
                    "Reason": item.get("reason", "")
                })

            st.dataframe(skipped_rows, width="stretch", hide_index=True)

    st.markdown("### Batch File")
    st.caption(f"Saved batch table: {BATCH_REPLAY_CSV}")



with tab_portfolio:
    st.markdown("## Portfolio Snapshot")
    st.caption("Manual snapshot only. This helps P&L readiness but does not connect to a broker.")

    current = load_json(PORTFOLIO_SNAPSHOT, {})
    positions = current.get("positions", {})

    with st.form("portfolio_snapshot_form", clear_on_submit=True):
        ticker = st.text_input("Ticker", value="AAPL", key="portfolio_ticker")

        col1, col2, col3 = st.columns(3)
        with col1:
            quantity = st.number_input("Quantity", value=0.0)
        with col2:
            average_cost = st.number_input("Average cost", value=0.0)
        with col3:
            current_price = st.number_input("Current price", value=0.0)

        col4, col5 = st.columns(2)
        with col4:
            market_value = st.number_input("Market value", value=0.0)
        with col5:
            unrealized_pnl = st.number_input("Unrealized P&L", value=0.0)

        notes = st.text_area("Notes", value="", key="portfolio_notes")

        submitted = st.form_submit_button("Save Portfolio Snapshot", use_container_width=True)

        if submitted:
            current.setdefault("positions", {})
            current["positions"][ticker.upper()] = {
                "ticker": ticker.upper(),
                "quantity": quantity,
                "average_cost": average_cost,
                "current_price": current_price,
                "market_value": market_value,
                "unrealized_pnl": unrealized_pnl,
                "notes": notes,
                "updated_at": now_utc(),
                "advisory_only": True
            }
            current["updated_at"] = now_utc()
            current["source"] = "decision_entry_app"
            current["advisory_only"] = True

            save_json(PORTFOLIO_SNAPSHOT, current)
            run_decision_engine()
            st.success(f"Portfolio snapshot saved for {ticker.upper()}")

    if positions:
        st.markdown("### Current Saved Positions")
        rows = list(positions.values())
        st.dataframe(rows, width="stretch", hide_index=True)
    else:
        st.caption("No saved portfolio positions yet.")

# ============================================================

try:
    import subprocess as _hermes_shutdown_subprocess

    with st.sidebar:
        st.markdown("---")
        

        if st.button("Shutdown Hermes Apps", key="shutdown_hermes_apps_global", type="secondary", use_container_width=True):
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

            st.warning("Shutdown requested. Hermes servers will stop. Close browser tabs manually.")
            st.stop()

except Exception as _shutdown_error:
    try:
        with st.sidebar:
            st.caption(f"Shutdown control unavailable: {_shutdown_error}")
    except Exception:
        pass


