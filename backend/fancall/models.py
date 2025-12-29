"""
Fancall SQLAlchemy models
"""

from aioia_core.models import BaseModel
from sqlalchemy_mixins import SerializeMixin  # type: ignore


class DBLiveRoom(BaseModel, SerializeMixin):
    """LiveRoom database model"""

    __tablename__ = "live_rooms"
