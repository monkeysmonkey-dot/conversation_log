import os, ast
from pathlib import Path
from collections import defaultdict
from datetime import datetime

BASE = Path(r"C:\Users\Abe\hermes agent\project\stock manager")
REPORT = BASE / "reports/system_audit/full_system_audit.md"

FUNCTIONS = defaultdict(list)
FILES = []

def scan_file(path):
    try:
        code = path.read_text(errors="ignore")
        tree = ast.parse(code)
    except:
        return

    funcs = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            FUNCTIONS[node.name].append(str(path))
            funcs.append(node.name)

    FILES.append((str(path), funcs))

def scan_all():
    for root, dirs, files in os.walk(BASE):
        if ".git" in root or "__pycache__" in root:
            continue
        for f in files:
            if f.endswith(".py"):
                scan_file(Path(root)/f)

def generate():
    lines = []
    lines.append("# FULL SYSTEM AUDIT\n")
    lines.append(f"Generated: {datetime.now()}\n")

    lines.append("## Files\n")
    for f, funcs in FILES:
        lines.append(f"- {f} | {len(funcs)} functions")

    lines.append("\n## Duplicate Functions\n")
    for fn, loc in FUNCTIONS.items():
        if len(loc) > 1:
            lines.append(f"### {fn}")
            for l in loc:
                lines.append(f"- {l}")

    REPORT.write_text("\n".join(lines))
    print("✅ Audit complete")

if __name__ == "__main__":
    scan_all()
    generate()
