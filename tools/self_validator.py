from datetime import datetime, timezone

def validate_output(parsed):
    required = [
        "system_version",
        "run_mode",
        "step_0_input_summary",
        "step_1_macro",
        "step_2_signal",
        "step_3_risk",
        "step_4_portfolio",
        "step_5_council",
        "step_6_performance",
        "step_7_stability",
        "summary"
    ]

    missing = [k for k in required if k not in parsed]

    return {
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "valid": len(missing) == 0,
        "missing_keys": missing
    }
