"""
Unit tests for the call memory routes and the memory loaded on dispatch
"""

import unittest
from unittest.mock import AsyncMock, patch

from aioia_core.models import Base
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from fancall.api.router import LiveRoomRouter
from fancall.factories import LiveRoomRepositoryFactory
from fancall.repositories.call_memory_repository import CallMemoryRepository
from fancall.schemas import (
    AgentDispatchRequest,
    LiveRoom,
    LiveRoomCreate,
    LiveRoomUpdate,
    MemoryLine,
)
from fancall.services.livekit_service import LiveKitDispatchResponse
from fancall.settings import LiveKitSettings


class CallMemoryRoutesTest(unittest.TestCase):
    def setUp(self) -> None:
        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(engine)
        self.session_factory = sessionmaker(bind=engine)
        live_room_router = LiveRoomRouter(
            livekit_settings=LiveKitSettings(
                url="wss://x", api_key="k", api_secret="s"
            ),
            model_class=LiveRoom,
            create_schema=LiveRoomCreate,
            update_schema=LiveRoomUpdate,
            db_session_factory=self.session_factory,
            repository_factory=LiveRoomRepositoryFactory(self.session_factory),
            user_info_provider=None,
            jwt_secret_key=None,
            resource_name="live-rooms",
            tags=["Fancall"],
        )
        self.app = FastAPI()
        self.app.include_router(live_room_router.get_router())
        self.user = "fan-1"
        self.app.dependency_overrides[live_room_router.get_current_user_id_dep] = (
            lambda: self.user
        )
        self.client = TestClient(self.app)

    def _recent(self, user: str = "fan-1", key: str = "t1") -> list[str]:
        with self.session_factory() as session:
            return [
                line.text for line in CallMemoryRepository(session).recent(user, key)
            ]

    def test_signed_in_fan_adds_lines(self):
        response = self.client.post(
            "/live-rooms/memory",
            json={"memoryKey": "t1", "lines": [{"speaker": "fan", "text": "hi"}]},
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self._recent(), ["hi"])

    def test_lines_go_to_the_signed_in_fan_only(self):
        self.client.post(
            "/live-rooms/memory",
            json={"memoryKey": "t1", "lines": [{"speaker": "fan", "text": "mine"}]},
        )
        self.assertEqual(self._recent("fan-2"), [])

    def test_too_many_lines_in_one_request_are_refused(self):
        lines = [{"speaker": "fan", "text": str(i)} for i in range(51)]
        response = self.client.post(
            "/live-rooms/memory", json={"memoryKey": "t1", "lines": lines}
        )
        self.assertEqual(response.status_code, 422)

    def test_forget_removes_the_memory(self):
        self.client.post(
            "/live-rooms/memory",
            json={"memoryKey": "t1", "lines": [{"speaker": "fan", "text": "a"}]},
        )
        self.assertEqual(self.client.delete("/live-rooms/memory/t1").status_code, 204)
        self.assertEqual(self._recent(), [])

    def test_anonymous_fan_is_refused(self):
        self.app.dependency_overrides.clear()
        self.assertEqual(
            self.client.post(
                "/live-rooms/memory", json={"memoryKey": "t1", "lines": []}
            ).status_code,
            401,
        )
        self.assertEqual(self.client.delete("/live-rooms/memory/t1").status_code, 401)

    def _dispatch(self, body: dict) -> AgentDispatchRequest:
        room = self.client.post("/live-rooms").json()["data"]["id"]
        dispatch = AsyncMock(
            return_value=LiveKitDispatchResponse(
                dispatch_id="d", room_name=room, agent_name="a"
            )
        )
        with patch("fancall.api.router.LiveKitService.dispatch_agent", new=dispatch):
            response = self.client.post(f"/live-rooms/{room}/dispatch", json=body)
        self.assertEqual(response.status_code, 200)
        return dispatch.call_args.args[0]

    def test_dispatch_loads_the_stored_memory(self):
        with self.session_factory() as session:
            CallMemoryRepository(session).append(
                "fan-1", "t1", [MemoryLine(speaker="fan", text="exam tomorrow")]
            )
        sent = self._dispatch({"memoryKey": "t1"})
        self.assertEqual([line.text for line in sent.memory], ["exam tomorrow"])

    def test_dispatch_keeps_memory_the_host_sent(self):
        with self.session_factory() as session:
            CallMemoryRepository(session).append(
                "fan-1", "t1", [MemoryLine(speaker="fan", text="stored")]
            )
        sent = self._dispatch(
            {"memoryKey": "t1", "memory": [{"speaker": "fan", "text": "from host"}]}
        )
        self.assertEqual([line.text for line in sent.memory], ["from host"])

    def test_dispatch_without_a_key_loads_nothing(self):
        with self.session_factory() as session:
            CallMemoryRepository(session).append(
                "fan-1", "t1", [MemoryLine(speaker="fan", text="stored")]
            )
        self.assertEqual(self._dispatch({}).memory, [])

    def test_dispatch_for_an_anonymous_fan_loads_nothing(self):
        with self.session_factory() as session:
            CallMemoryRepository(session).append(
                "fan-1", "t1", [MemoryLine(speaker="fan", text="stored")]
            )
        self.app.dependency_overrides.clear()
        self.assertEqual(self._dispatch({"memoryKey": "t1"}).memory, [])


if __name__ == "__main__":
    unittest.main()
