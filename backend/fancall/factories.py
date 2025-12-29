"""
Fancall factories
"""

from __future__ import annotations

from aioia_core.factories import BaseRepositoryFactory
from sqlalchemy.orm import sessionmaker

from fancall.managers import DatabaseLiveRoomManager


class LiveRoomManagerFactory(BaseRepositoryFactory[DatabaseLiveRoomManager]):
    """LiveRoom manager factory"""

    def __init__(self, db_session_factory: sessionmaker):
        super().__init__(
            db_session_factory=db_session_factory,
            repository_class=DatabaseLiveRoomManager,
        )
