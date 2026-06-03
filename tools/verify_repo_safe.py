import re
from pathlib import Path
import sys

BASE = Path(r"C:\Users\Abe\hermes agent\project\stock manager")

# ✅ Only detect REAL secrets (not keywords)
PATTERNS = [
    r"sk-[A-Za-z0-9]{10,}",         # OpenAI-style keys
    r"=\s*[A-Za-z0-9]{20,}",        # long token-like values
    r"[REDACTED][A-Za-z0-9\-_\.]+"   # bearer tokens
]

# ✅ Ignore folders that should never be scanned
IGNORE = [
    ".git",
    "__pycache__",
    ".backup",
    "backup",
    "logs",
    "browser_profiles",
    "reports/handoff"
]

def is_ignored(path):
    return any(i in str(path) for i in IGNORE)

def scan():
    issues = []

    for f in BASE.rglob("*"):
        if is_ignored(f):
            continue

        if f.is_file():
            try:
                text = f.read_text(errors="ignore")
            except:
                continue

            for pat in PATTERNS:
                if re.search(pat, text):
                    issues.append(str(f))
                    break

    return issues


def main():
    findings = scan()

    if findings:
        print("\n🚨 REAL SECRETS DETECTED:\n")
        for f in findings:
            print("❌", f)

        print("\n❌ BLOCKING PUSH — FIX REQUIRED\n")
        sys.exit(1)
    else:
        print("\n✅ CLEAN — SAFE FOR GITHUB ✓\n")


if __name__ == "__main__":
    main()
