import os
from datetime import datetime

def build_daily_report(base, parsed):
    os.makedirs(os.path.join(base, "reports", "daily"), exist_ok=True)

    path = os.path.join(
        base,
        "reports",
        "daily",
        f"daily_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    )

    summary = parsed.get("summary", {}) if isinstance(parsed, dict) else {}

    with open(path, "w", encoding="utf-8") as f:
        f.write("# Daily Stock Manager Report\\n\\n")
        f.write(f"Generated: {datetime.now().isoformat()}\\n\\n")
        f.write("## Summary\\n\\n")
        f.write(str(summary))

    return path
