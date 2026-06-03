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
