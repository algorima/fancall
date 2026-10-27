"""
Fancall SQLAlchemy models
"""

from aioia_core.models import BaseModel
from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy_mixins import SerializeMixin  # type: ignore


class DBLiveRoom(BaseModel, SerializeMixin):
    """LiveRoom database model"""

    __tablename__ = "live_rooms"


class DBCallMemory(BaseModel, SerializeMixin):
    """One spoken line of an earlier call, kept per signed-in fan and trainee"""

    __tablename__ = "call_memories"
    __table_args__ = (
        Index(
            "ix_call_memories_fan_trainee_time", "user_id", "memory_key", "created_at"
        ),
    )

    user_id: Mapped[str] = mapped_column(String, nullable=False)
    # Host-chosen id of the trainee (or character) the fan talked to
    memory_key: Mapped[str] = mapped_column(String, nullable=False)
    speaker: Mapped[str] = mapped_column(String(8), nullable=False)
    text: Mapped[str] = mapped_column(String(500), nullable=False)
