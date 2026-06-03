from uuid import uuid4
from datetime import datetime

class Claim:

    def __init__(
        self,
        text,
        source_id,
        company=None,
        sector=None,
        confidence=0.5
    ):

        self.id = str(uuid4())

        self.text = text

        self.source_id = source_id

        self.company = company

        self.sector = sector

        self.confidence = confidence

        self.verified = False

        self.related_claims = []

        self.related_entities = []

        self.created_at = datetime.utcnow().isoformat()

    def to_dict(self):

        return {
            "id": self.id,
            "text": self.text,
            "source_id": self.source_id,
            "company": self.company,
            "sector": self.sector,
            "confidence": self.confidence,
            "verified": self.verified,
            "related_claims": self.related_claims,
            "related_entities": self.related_entities,
            "created_at": self.created_at
        }
