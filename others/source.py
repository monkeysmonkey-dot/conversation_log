from uuid import uuid4
from datetime import datetime

class Source:

    def __init__(
        self,
        title,
        url,
        source_type="unknown"
    ):

        self.id = str(uuid4())

        self.title = title

        self.url = url

        self.source_type = source_type

        self.created_at = datetime.utcnow().isoformat()

    def to_dict(self):

        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "source_type": self.source_type,
            "created_at": self.created_at
        }
