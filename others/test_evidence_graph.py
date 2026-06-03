from evidence.claims.claim import Claim
from evidence.sources.source import Source

from evidence.graph_engine import EvidenceGraph

from evidence.verification.verifier import EvidenceVerifier

from evidence.vault_writer.vault_writer import VaultWriter

graph = EvidenceGraph()

source = Source(
    title="NVDA Earnings",
    url="https://sec.gov/nvda"
)

claim = Claim(
    text="AI demand accelerating",
    source_id=source.id,
    company="NVDA",
    sector="AI"
)

verifier = EvidenceVerifier()

claim = verifier.verify(
    claim,
    source
)

graph.add_source(source)

graph.add_claim(claim)

graph.link_claim_to_source(
    claim.id,
    source.id
)

graph.link_entity(
    claim.id,
    "TSMC"
)

graph.export_graph(
    "hermes_core/data/graph/evidence_graph.json"
)

vault = VaultWriter(
    "hermes_core/data/vault"
)

vault.write_company_note(
    company="NVDA",
    claims=[
        claim.text
    ],
    sources=[
        source.title
    ],
    related_entities=[
        "TSMC",
        "AI Infrastructure"
    ]
)

print("SUCCESS")
