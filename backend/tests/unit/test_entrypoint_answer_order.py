"""
Unit tests for the order of answering and avatar startup in the agent entrypoint
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fancall.agent.worker import entrypoint
from fancall.persona import DEFAULT_PERSONA
from fancall.schemas import AgentDispatchRequest
from fancall.settings import (
    ElevenLabsSettings,
    FancallCallSettings,
    FancallModelSettings,
    LiveKitSettings,
    SimliSettings,
)


def _make_ctx(metadata: AgentDispatchRequest) -> MagicMock:
    ctx = MagicMock()
    ctx.connect = AsyncMock()
    ctx.job.metadata = metadata.model_dump_json(by_alias=True)
    return ctx


@patch("fancall.agent.worker.run_call_timer", new_callable=AsyncMock)
@patch("fancall.agent.worker.AgentSession")
@patch("fancall.agent.worker.elevenlabs")
@patch("fancall.agent.worker.openai")
class TestEntrypointAnswerOrder(unittest.IsolatedAsyncioTestCase):
    """The avatar must not start before the fan answers"""

    async def _run(
        self,
        metadata: AgentDispatchRequest,
        wait_for_answer: AsyncMock,
        start_avatar: AsyncMock,
        livekit_settings: LiveKitSettings | None = None,
    ) -> MagicMock:
        ctx = _make_ctx(metadata)
        with (
            patch("fancall.agent.worker.wait_for_answer", wait_for_answer),
            patch("fancall.agent.worker.start_avatar", start_avatar),
        ):
            await entrypoint(
                ctx,
                DEFAULT_PERSONA,
                livekit_settings or LiveKitSettings(),
                MagicMock(),
                ElevenLabsSettings(),
                SimliSettings(),
                FancallModelSettings(),
                FancallCallSettings(),
            )
        return ctx

    async def test_avatar_starts_after_fan_answers(
        self,
        _openai: MagicMock,
        _eleven: MagicMock,
        session_cls: MagicMock,
        _t: AsyncMock,
    ) -> None:
        """wait_for_answer runs before start_avatar on a video call"""
        session_cls.return_value.start = AsyncMock()
        order = MagicMock()
        wait = AsyncMock(return_value=True)
        avatar = AsyncMock()
        order.attach_mock(wait, "wait_for_answer")
        order.attach_mock(avatar, "start_avatar")

        await self._run(AgentDispatchRequest(), wait, avatar)

        names = [call[0] for call in order.mock_calls]
        self.assertEqual(names, ["wait_for_answer", "start_avatar"])

    async def test_unanswered_call_never_starts_avatar(
        self,
        _openai: MagicMock,
        _eleven: MagicMock,
        session_cls: MagicMock,
        _t: AsyncMock,
    ) -> None:
        """A declined or missed call opens no Simli session"""
        session_cls.return_value.start = AsyncMock()
        avatar = AsyncMock()

        await self._run(AgentDispatchRequest(), AsyncMock(return_value=False), avatar)

        avatar.assert_not_awaited()
        session_cls.return_value.start.assert_not_called()

    async def test_dial_out_does_not_wait_for_fan_in_room(
        self,
        _openai: MagicMock,
        _eleven: MagicMock,
        session_cls: MagicMock,
        _t: AsyncMock,
    ) -> None:
        """Dialing a phone skips wait_for_answer; dial_phone waits for the pickup"""
        session_cls.return_value.start = AsyncMock()
        wait = AsyncMock(return_value=False)
        with patch(
            "fancall.agent.worker.dial_phone", AsyncMock(return_value=True)
        ) as dial:
            await self._run(
                AgentDispatchRequest(phone_number="+821012345678"),
                wait,
                AsyncMock(),
                LiveKitSettings(sip_outbound_trunk_id="trunk-1"),
            )

        wait.assert_not_awaited()
        dial.assert_awaited_once()
        session_cls.return_value.start.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
