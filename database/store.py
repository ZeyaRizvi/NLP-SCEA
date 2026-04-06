from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ComplaintRecord:
    id: str
    text: str
    categories: List[str]
    summary: str


class InMemoryComplaintStore:
    """
    Minimal persistence placeholder.

    Replace with a real DB layer (e.g., SQLAlchemy + PostgreSQL) when needed.
    """

    def __init__(self) -> None:
        self._records: Dict[str, ComplaintRecord] = {}

    def upsert(self, record: ComplaintRecord) -> None:
        self._records[record.id] = record

    def get(self, record_id: str) -> Optional[ComplaintRecord]:
        return self._records.get(record_id)

