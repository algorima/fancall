"""
Stored lines of earlier calls, per signed-in fan and trainee
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from fancall.models import DBCallMemory
from fancall.schemas import MemoryLine

# What the trainee can recall at most; older lines are dropped as new ones arrive
MAX_STORED_LINES = 200


class CallMemoryRepository:
    """Lines of earlier calls. A fan only ever reaches their own (user_id) lines."""

    def __init__(self, db_session: Session):
        self._session = db_session

    def append(self, user_id: str, memory_key: str, lines: list[MemoryLine]) -> None:
        """Add lines in order, then keep only the latest MAX_STORED_LINES."""
        if not lines:
            return
        start = datetime.now(timezone.utc)
        for offset, line in enumerate(lines):
            self._session.add(
                DBCallMemory(
                    user_id=user_id,
                    memory_key=memory_key,
                    speaker=line.speaker,
                    text=line.text,
                    # Lines of one call share a moment; a microsecond apart keeps their order
                    created_at=start + timedelta(microseconds=offset),
                )
            )
        self._session.flush()
        self._trim(user_id, memory_key)
        self._session.commit()

    def recent(
        self, user_id: str, memory_key: str, limit: int = MAX_STORED_LINES
    ) -> list[MemoryLine]:
        """The latest lines, oldest first."""
        rows = self._session.scalars(
            select(DBCallMemory)
            .where(
                DBCallMemory.user_id == user_id,
                DBCallMemory.memory_key == memory_key,
            )
            .order_by(DBCallMemory.created_at.desc())
            .limit(limit)
        ).all()
        return [
            MemoryLine(speaker=row.speaker, text=row.text)  # type: ignore[arg-type]
            for row in reversed(rows)
        ]

    def delete(self, user_id: str, memory_key: str) -> int:
        """Forget everything this fan said to and heard from this trainee."""
        result = self._session.execute(
            delete(DBCallMemory).where(
                DBCallMemory.user_id == user_id,
                DBCallMemory.memory_key == memory_key,
            )
        )
        self._session.commit()
        return result.rowcount or 0  # type: ignore[attr-defined]

    def _trim(self, user_id: str, memory_key: str) -> None:
        keep = (
            select(DBCallMemory.id)
            .where(
                DBCallMemory.user_id == user_id, DBCallMemory.memory_key == memory_key
            )
            .order_by(DBCallMemory.created_at.desc())
            .limit(MAX_STORED_LINES)
        )
        self._session.execute(
            delete(DBCallMemory).where(
                DBCallMemory.user_id == user_id,
                DBCallMemory.memory_key == memory_key,
                DBCallMemory.id.not_in(keep),
            )
        )
