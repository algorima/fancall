"""
Unit tests for the public dispatch route
"""

import unittest
from unittest.mock import AsyncMock, patch

from aioia_core.settings import JWTSettings
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from fancall.api.router import create_fancall_router
from fancall.factories import LiveRoomRepositoryFactory
from fancall.models import DBLiveRoom
from fancall.services.livekit_service import LiveKitDispatchResponse
from fancall.settings import LiveKitSettings


class TestPublicDispatchRoute(unittest.TestCase):
    """Tests for POST /live-rooms/{id}/dispatch"""

    def setUp(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        DBLiveRoom.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine)
        app = FastAPI()
        app.include_router(
            create_fancall_router(
                livekit_settings=LiveKitSettings(),
                jwt_settings=JWTSettings(secret_key="x" * 32),
                db_session_factory=session_factory,
                repository_factory=LiveRoomRepositoryFactory(session_factory),
                user_info_provider=object(),  # type: ignore[arg-type]
            )
        )
        self.client = TestClient(app)
        self.room_id = self.client.post("/live-rooms").json()["data"]["id"]

    def _dispatch(self, body: dict) -> tuple[int, bool]:
        response_value = LiveKitDispatchResponse("dispatch-1", self.room_id, "fancall")
        with patch(
            "fancall.api.router.LiveKitService.dispatch_agent",
            new=AsyncMock(return_value=response_value),
        ) as dispatch_agent:
            response = self.client.post(
                f"/live-rooms/{self.room_id}/dispatch", json=body
            )
        return response.status_code, dispatch_agent.called

    def test_rejects_phone_number(self):
        """Test anonymous callers cannot make the agent dial any phone number"""
        status_code, dispatched = self._dispatch({"phoneNumber": "+821012345678"})

        self.assertEqual(status_code, 403)
        self.assertFalse(dispatched)

    def test_video_call_dispatch_still_works(self):
        """Test the existing video call dispatch is unchanged"""
        status_code, dispatched = self._dispatch({})

        self.assertEqual(status_code, 200)
        self.assertTrue(dispatched)


if __name__ == "__main__":
    unittest.main()
