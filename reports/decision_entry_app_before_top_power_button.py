import json
from pathlib import Path
from datetime import datetime, timezone

import streamlit as st

BASE = Path(__file__).resolve().parents[1]

MANUAL_ACTIONS = BASE / "data" / "manual_actions_journal.jsonl"
AGENT_SUGGESTIONS = BASE / "data" / "agent_suggestions_journal.jsonl"
THESIS_HEALTH = BASE / "data" / "thesis_health_journal.jsonl"
PORTFOLIO_SNAPSHOT = BASE / "data" / "portfolio_snapshot.json"
DECISION_STATUS = BASE / "features" / "latest_decision_data_status.json"


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

tab_manual, tab_agent, tab_thesis, tab_portfolio = st.tabs([
    "Log Manual Action",
    "Log Agent Suggestion",
    "Update Thesis Health",
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
# Hermes Shutdown Button
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


