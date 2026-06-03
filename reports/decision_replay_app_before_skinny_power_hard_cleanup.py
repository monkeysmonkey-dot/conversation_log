import json
import subprocess
from pathlib import Path

import streamlit as st

BASE = Path(__file__).resolve().parents[1]

REPLAY_PATH = BASE / "features" / "latest_decision_replay.json"
DECISION_STATUS_PATH = BASE / "features" / "latest_decision_data_status.json"


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
        font-size: 0.72rem;
        margin-top: -0.35rem;
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
# Hermes Top Power Button
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
        font-size: 0.72rem;
        margin-top: -0.35rem;
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


render_hermes_top_power_button()

st.title("Hermes Decision Replay")
st.caption("Replay readiness for manual actions, agent suggestions, thesis records, and portfolio snapshots. Advisory only.")

if st.button("Refresh Decision Data + Replay", width="stretch"):
    r1 = run_cmd(["py", "tools\\decision_data_engine.py"])
    r2 = run_cmd(["py", "tools\\decision_replay_engine.py"])
    st.toast(f"Decision data: {r1.get('status')} | Replay: {r2.get('status')}")
    st.rerun()

replay = load_json(REPLAY_PATH, {})
decision = load_json(DECISION_STATUS_PATH, {})

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

tab_manual, tab_agent, tab_thesis, tab_files = st.tabs([
    "Manual Action Replay",
    "Agent Suggestion Replay",
    "Thesis Health",
    "Files"
])

with tab_manual:
    st.markdown("## Manual Action Replay")
    rows = replay.get("manual_replays", [])
    if rows:
        st.dataframe(rows, width="stretch", hide_index=True)
    else:
        st.warning("No manual actions logged yet.")

with tab_agent:
    st.markdown("## Agent Suggestion Replay")
    rows = replay.get("agent_replays", [])
    if rows:
        st.dataframe(rows, width="stretch", hide_index=True)
    else:
        st.warning("No agent suggestions logged yet.")

with tab_thesis:
    st.markdown("## Latest Thesis By Ticker")
    thesis = replay.get("latest_thesis_by_ticker", {})
    if thesis:
        rows = list(thesis.values())
        st.dataframe(rows, width="stretch", hide_index=True)
    else:
        st.warning("No thesis health records logged yet.")

with tab_files:
    st.markdown("## Replay Files")
    files = replay.get("files", {})
    if files:
        for key, value in files.items():
            st.code(f"{key}: {value}")
    else:
        st.caption("No replay file metadata available.")

# ============================================================

try:
    import subprocess as _hermes_shutdown_subprocess

    with st.sidebar:
        st.markdown("---")
        st.caption("Hermes App Control")

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


