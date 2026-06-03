import os
from datetime import datetime, timezone

def compile_daily_memory(base, run_summary):
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = os.path.join(base, "memory", "daily", f"{day}.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "a", encoding="utf-8") as f:
        f.write("\\n\\n## Run Summary\\n")
        f.write(f"- Time: {datetime.now(timezone.utc).isoformat()}\\n")
        f.write(f"- Summary: {run_summary}\\n")

    index_path = os.path.join(base, "memory", "index.md")

    if not os.path.exists(index_path):
        with open(index_path, "w", encoding="utf-8") as f:
            f.write("# Stock Manager Memory Index\\n\\n")
            f.write("- SQLite is the structured source of truth.\\n")
            f.write("- Obsidian vault stores human-readable reports and thesis notes.\\n")
            f.write("- Chroma stores semantic memory vectors.\\n")
