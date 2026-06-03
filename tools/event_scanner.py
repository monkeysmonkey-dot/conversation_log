from datetime import datetime, timezone

def run():
    return {
        "earnings_calendar": [],
        "fed_events": [],
        "cpi_events": [],
        "policy_events": [],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
