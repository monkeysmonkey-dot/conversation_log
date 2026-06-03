import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]
CANDIDATES = BASE / "features" / "latest_candidates.json"
THEME_JSON = BASE / "features" / "latest_theme_wave_analysis.json"
OUT = BASE / "reports" / "weekly" / "latest_saturday_relationship_expansion.md"

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default

def main():
    candidates = load_json(CANDIDATES, {}).get("top_candidates", [])
    theme = load_json(THEME_JSON, {})

    OUT.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# Saturday Relationship / Theme Expansion")
    lines.append("")
    lines.append(f"Created: {utc_now()}")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append("- Compare each prospect to sector leader.")
    lines.append("- Compare peers, competitors, inverse competitors.")
    lines.append("- Map upstream, downstream, adjacent names.")
    lines.append("- Identify laggers that may benefit next.")
    lines.append("- Build relationship/theme chain report.")
    lines.append("")

    lines.append("## Top Prospect Relationship Review")
    lines.append("")

    for c in candidates[:10]:
        rel = c.get("relationship_context", {})
        compare = c.get("sector_leader_comparison", {})
        peer_effects = c.get("sector_competitor_effects", [])
        phase = c.get("theme_phase", {})

        lines.append(f"### {c.get('ticker')}")
        lines.append("")
        lines.append(f"- Candidate score: {c.get('candidate_score')}")
        lines.append(f"- Conviction rate: {c.get('conviction_rate')}%")
        lines.append(f"- Sector leader / benchmark: {compare.get('leader')}")
        lines.append(f"- Relative setup: {compare.get('relative_setup')}")
        lines.append(f"- Move scope determined: {rel.get('move_scope_determined')}")
        lines.append(f"- Primary theme: {rel.get('primary_theme')}")
        lines.append(f"- Theme chain: {rel.get('theme_chain_summary')}")
        lines.append(f"- Upstream: {', '.join(rel.get('upstream', [])) if rel.get('upstream') else 'None mapped'}")
        lines.append(f"- Downstream: {', '.join(rel.get('downstream', [])) if rel.get('downstream') else 'None mapped'}")
        lines.append(f"- Adjacent: {', '.join(rel.get('adjacent', [])) if rel.get('adjacent') else 'None mapped'}")
        lines.append(f"- Economic transmission: {rel.get('economic_transmission')}")
        lines.append(f"- Theme phase: {phase.get('phase')}")
        lines.append(f"- Bubble risk: {phase.get('bubble_risk')}")
        lines.append("")
        lines.append("Peer / competitor effect:")
        if peer_effects:
            for p in peer_effects:
                lines.append(f"- {p.get('peer')}: {p.get('effect')} — {p.get('note')}")
        else:
            lines.append("- No peer effects mapped.")
        lines.append("")

    lines.append("## Next Beneficiaries From Theme Engine")
    lines.append("")
    for b in theme.get("top_next_beneficiaries", [])[:20]:
        lines.append(f"- {b.get('name')}: relationship score {b.get('theme_score')}")

    lines.append("")
    lines.append("## Risk Chain")
    lines.append("")
    for r in theme.get("risk_flags", []):
        lines.append(f"- {r}")

    OUT.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "report": str(OUT)
    }, indent=2))

if __name__ == "__main__":
    main()
