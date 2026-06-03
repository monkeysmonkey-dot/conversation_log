import json
import re
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]
INPUT_DIRS = [
    BASE / "data" / "qualitative_raw",
    BASE / "reports" / "daily",
    BASE / "reports" / "weekly"
]
OUT_JSON = BASE / "features" / "latest_association_intelligence.json"
OUT_MD = BASE / "reports" / "macro" / "latest_association_intelligence.md"

KEY_ENTITIES = [
    "Trump", "Fed", "Powell", "FOMC", "Treasury", "White House",
    "Nvidia", "NVDA", "Dell", "DELL", "Intel", "INTC", "Microsoft", "MSFT",
    "Apple", "AAPL", "Meta", "META", "Google", "GOOGL", "Amazon", "AMZN",
    "TSMC", "TSM", "Broadcom", "AVGO", "AMD", "Micron", "MU",
    "uranium", "nuclear", "Greenland", "Canada", "Mexico", "China",
    "critical minerals", "rare earths", "data center", "power shortage"
]

ASSOCIATION_PATTERNS = [
    "appeared with",
    "joined by",
    "mentioned",
    "partnered with",
    "announced with",
    "met with",
    "interview",
    "CEO",
    "policy",
    "investment",
    "stake",
    "national security",
    "critical asset",
    "supply chain"
]

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def read_text_files():
    docs = []

    for d in INPUT_DIRS:
        if not d.exists():
            continue

        for path in d.glob("*.md"):
            docs.append((path, path.read_text(encoding="utf-8", errors="ignore")))

        for path in d.glob("*.txt"):
            docs.append((path, path.read_text(encoding="utf-8", errors="ignore")))

    return docs

def extract_sentences(text):
    text = re.sub(r"\s+", " ", text)
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if len(p.strip()) > 30]


def normalize_sentence_for_dedupe(sentence):
    s = re.sub(r"\s+", " ", str(sentence).strip().lower())
    s = re.sub(r"[^a-z0-9\s$.-]", "", s)
    return s[:240]


def find_associations():
    docs = read_text_files()
    hits = []
    seen = set()

    for path, text in docs:
        sentences = extract_sentences(text)

        for s in sentences:
            entities = sorted(list(dict.fromkeys([e for e in KEY_ENTITIES if e.lower() in s.lower()])))
            patterns = sorted(list(dict.fromkeys([p for p in ASSOCIATION_PATTERNS if p.lower() in s.lower()])))

            # Avoid weak one-entity noise unless there is a strong association pattern.
            strong_pattern = any(
                p in patterns
                for p in [
                    "appeared with",
                    "joined by",
                    "partnered with",
                    "announced with",
                    "met with",
                    "national security",
                    "critical asset",
                    "supply chain",
                    "investment",
                    "stake"
                ]
            )

            if len(entities) < 2 and not strong_pattern:
                continue

            association_type = classify_association(s, entities, patterns)
            why = explain_association(s, entities, patterns)

            # Dedupe by entity set + association type + normalized sentence.
            key = (
                tuple(entities),
                association_type,
                normalize_sentence_for_dedupe(s)
            )

            if key in seen:
                continue

            seen.add(key)

            hits.append({
                "source": str(path),
                "sentence": s[:1000],
                "entities": entities,
                "patterns": patterns,
                "association_type": association_type,
                "why_it_matters": why
            })

    # Prefer richer hits first.
    hits = sorted(
        hits,
        key=lambda x: (
            len(x.get("entities", [])),
            len(x.get("patterns", []))
        ),
        reverse=True
    )

    return hits[:120]


def classify_association(sentence, entities, patterns):
    s = sentence.lower()

    if "national security" in s or "critical asset" in s or "stake" in s:
        return "policy_or_national_security_association"

    if "ceo" in s or "interview" in s or "appeared with" in s or "joined by" in s:
        return "executive_signal_or_relationship"

    if "supply chain" in s or "critical minerals" in s or "rare earth" in s:
        return "supply_chain_or_resource_pressure"

    if "data center" in s or "power" in s or "nuclear" in s or "uranium" in s:
        return "infrastructure_or_energy_transmission"

    if len(entities) >= 2:
        return "entity_co_mention"

    return "general_association"

def explain_association(sentence, entities, patterns):
    if not entities:
        return "Potential qualitative signal. Needs manual/agent follow-up."

    if any(x in entities for x in ["Nvidia", "NVDA"]) and any(x in entities for x in ["Dell", "DELL"]):
        return "Nvidia appearing with Dell may point to server/data-center supply chain or AI infrastructure partnership relevance."

    if any(x in entities for x in ["Trump"]) and any(x in entities for x in ["Intel", "INTC"]):
        return "Trump/Intel association may point to national security, domestic semiconductor capacity, or policy-driven critical asset logic."

    if any(x in entities for x in ["China"]) and ("critical minerals" in sentence.lower() or "rare earth" in sentence.lower()):
        return "China/resource association may point to geopolitical supply chain pressure affecting critical minerals and downstream technology sectors."

    if "power" in sentence.lower() or "nuclear" in sentence.lower() or "uranium" in sentence.lower():
        return "Power/nuclear/uranium association may point to AI data-center energy demand transmission."

    return "Co-mention may indicate business, policy, supply-chain, or theme relationship. Needs qualitative agent to determine intent and investment relevance."

def main():
    hits = find_associations()

    payload = {
        "timestamp": utc_now(),
        "hits": hits
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = []
    lines.append("# Association Intelligence")
    lines.append("")
    lines.append(f"Created: {payload['timestamp']}")
    lines.append("")
    lines.append("## Key Association Hits")
    lines.append("")

    for h in hits[:50]:
        lines.append(f"### {h['association_type']}")
        lines.append(f"- Entities: {', '.join(h.get('entities', [])) if h.get('entities') else 'None'}")
        lines.append(f"- Patterns: {', '.join(h.get('patterns', [])) if h.get('patterns') else 'None'}")
        lines.append(f"- Why it matters: {h.get('why_it_matters')}")
        lines.append(f"- Source: {h.get('source')}")
        lines.append(f"- Text: {h.get('sentence')}")
        lines.append("")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "hits": len(hits),
        "json": str(OUT_JSON),
        "report": str(OUT_MD)
    }, indent=2))

if __name__ == "__main__":
    main()
