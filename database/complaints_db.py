import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, List, Optional


DB_PATH = os.getenv(
    "COMPLAINTS_DB_PATH",
    os.path.join(os.path.dirname(__file__), "complaints.sqlite3"),
)


@dataclass(frozen=True)
class ComplaintRow:
    id: int
    complaint: str
    issue: str
    location: str
    priority: str
    timestamp: str


@contextmanager
def _connect() -> Iterable[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                complaint TEXT NOT NULL,
                issue TEXT NOT NULL,
                location TEXT NOT NULL,
                priority TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
            """
        )
        conn.commit()


def insert_complaint(
    *,
    complaint: str,
    issue: str,
    location: str,
    priority: str,
    timestamp: Optional[str] = None,
) -> int:
    """
    Insert a complaint analysis record.

    Returns the new row id.
    """
    ts = timestamp or datetime.now(timezone.utc).isoformat()

    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO complaints (complaint, issue, location, priority, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (complaint, issue, location, priority, ts),
        )
        conn.commit()
        return int(cur.lastrowid)


def get_all_complaints() -> List[ComplaintRow]:
    with _connect() as conn:
        cur = conn.execute(
            """
            SELECT id, complaint, issue, location, priority, timestamp
            FROM complaints
            ORDER BY id DESC
            """
        )
        rows = cur.fetchall()

    return [
        ComplaintRow(
            id=int(r["id"]),
            complaint=str(r["complaint"]),
            issue=str(r["issue"]),
            location=str(r["location"]),
            priority=str(r["priority"]),
            timestamp=str(r["timestamp"]),
        )
        for r in rows
    ]

