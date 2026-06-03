import re
import shutil
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# =========================================================
# CONFIG
# =========================================================

BASE = Path(r"C:\Users\Abe\hermes agent\project\stock manager")

REPORT = BASE / "reports/system_audit/full_system_audit.md"

BACKUP_ROOT = BASE / "backup"
RUN = BACKUP_ROOT / f"duplicates_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

SUMMARY = BASE / "reports/system_audit/cleanup_summary.md"
INDEX_FILE = RUN / "backup_index.json"

RUN.mkdir(parents=True, exist_ok=True)

# =========================================================
# STEP 1 — PARSE DUPLICATES
# =========================================================

def extract_duplicate_groups():
    groups = defaultdict(list)

    if not REPORT.exists():
        print("❌ Audit report not found")
        return groups

    current_func = None

    for line in REPORT.read_text(errors="ignore").splitlines():
        line = line.strip()

        if line.startswith("###"):
            current_func = line.replace("###", "").strip()
            continue

        if line.startswith("- ") and current_func:
            path = line.replace("- ", "").strip()

            if path.endswith(".py"):
                groups[current_func].append(path)

    return groups


# =========================================================
# STEP 2 — PRIMARY VS DUPLICATE
# =========================================================

def decide_files_to_move(groups):
    keep = set()
    move = set()

    for func, files in groups.items():
        files = list(dict.fromkeys(files))

        if not files:
            continue

        primary = files[0]
        keep.add(primary)

        for f in files[1:]:
            move.add(f)

    return keep, move


# =========================================================
# STEP 3 — DEPENDENCY CHECK
# =========================================================

def is_file_used(filepath):
    name = Path(filepath).stem

    for f in BASE.rglob("*.py"):
        try:
            text = f.read_text(errors="ignore")
        except:
            continue

        if f != Path(filepath):
            if re.search(rf"\b{name}\b", text):
                return True

    return False


# =========================================================
# STEP 4 — SAFE MOVE
# =========================================================

def move_files(move_set):
    moved = []
    skipped = []
    index = []

    for f in move_set:
        src = Path(f)

        if not src.exists():
            continue

        if is_file_used(src):
            skipped.append(str(src))
            continue

        try:
            rel = src.relative_to(BASE)
        except:
            continue

        dest = RUN / rel
        dest.parent.mkdir(parents=True, exist_ok=True)

        shutil.move(str(src), str(dest))

        moved.append(str(rel))

        index.append({
            "original": str(src),
            "backup": str(dest)
        })

    INDEX_FILE.write_text(json.dumps(index, indent=2))

    return moved, skipped


# =========================================================
# STEP 5 — SUMMARY
# =========================================================

def write_summary(kept, moved, skipped):
    lines = []

    lines.append("# SAFE CLEANUP SUMMARY\n")
    lines.append(f"Generated: {datetime.now()}\n")
    lines.append(f"Backup: {RUN}\n")

    lines.append("## ✅ KEPT\n")
    for k in sorted(kept):
        lines.append(f"- {k}")

    lines.append("\n## 📦 MOVED\n")
    for m in moved:
        lines.append(f"- {m}")

    lines.append("\n## ⚠️ SKIPPED (IN USE)\n")
    for s in skipped:
        lines.append(f"- {s}")

    lines.append("\n✅ Nothing deleted — full rollback available")

    SUMMARY.write_text("\n".join(lines), encoding="utf-8")


# =========================================================
# MAIN
# =========================================================

def main():
    print("🔍 Parsing audit...")
    groups = extract_duplicate_groups()

    if not groups:
        print("✅ No duplicates found")
        return

    keep, move = decide_files_to_move(groups)

    print(f"📦 Moving {len(move)} duplicates safely...")

    moved, skipped = move_files(move)

    write_summary(keep, moved, skipped)

    print("\n✅ CLEANUP COMPLETE")
    print(f"Backup: {RUN}")
    print(f"Summary: {SUMMARY}")

if __name__ == "__main__":
    main()
