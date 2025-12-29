"""
Fancall repositories
"""

from __future__ import annotations

from typing import Any

from aioia_core.managers import BaseManager
from sqlalchemy.orm import Session

from fancall.models import DBLiveRoom
from fancall.schemas import LiveRoom, LiveRoomCreate, LiveRoomUpdate


def _convert_db_live_room_to_model(db_live_room: DBLiveRoom) -> LiveRoom:
    """Convert DBLiveRoom to LiveRoom model"""
    return LiveRoom.model_validate(db_live_room.to_dict())


def _convert_live_room_to_db_model(live_room: LiveRoomCreate) -> dict:
    """Convert LiveRoomCreate schema to dictionary for database storage"""
    # Use exclude_unset=True to follow database defaults for fields not provided by user
    return live_room.model_dump(exclude_unset=True)


class DatabaseLiveRoomRepository(
    BaseManager[LiveRoom, DBLiveRoom, LiveRoomCreate, LiveRoomUpdate]
):
    """Database implementation of LiveRoomRepository"""

    def __init__(self, db_session: Session):
        """
        Initialize DatabaseLiveRoomRepository.

        Args:
            db_session: SQLAlchemy session
        """
        super().__init__(
            db_session=db_session,
            db_model=DBLiveRoom,
            convert_to_model=_convert_db_live_room_to_model,
            convert_to_db_model=_convert_live_room_to_db_model,
        )

    def get_by_id(
        self, item_id: str, load_options: list[Any] | None = None
    ) -> LiveRoom | None:
        """Get LiveRoom by ID"""
        return super().get_by_id(item_id, load_options=load_options)

    def get_all(
        self,
        current: int = 1,
        page_size: int = 10,
        sort: list[tuple[str, str]] | None = None,
        filters: list[dict[str, Any]] | None = None,
        load_options: list[Any] | None = None,
    ) -> tuple[list[LiveRoom], int]:
        """Get list of LiveRooms"""
        return super().get_all(
            current, page_size, sort, filters, load_options=load_options
        )

    def create(self, schema: LiveRoomCreate) -> LiveRoom:
        """Create new LiveRoom"""
        return super().create(schema)

    def update(self, item_id: str, schema: LiveRoomUpdate) -> LiveRoom | None:
        """Update LiveRoom"""
        if not item_id:
            raise ValueError("LiveRoom ID is required for update")
        return super().update(item_id, schema)
