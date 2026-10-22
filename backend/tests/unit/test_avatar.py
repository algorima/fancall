"""
Unit tests for Simli avatar startup in the agent worker
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fancall.agent.worker import start_avatar
from fancall.settings import AvatarSettings, LiveKitSettings


class TestStartAvatar(unittest.IsolatedAsyncioTestCase):
    """Test cases for start_avatar"""

    async def _start(self, avatar_id: str | None, settings: AvatarSettings) -> None:
        await start_avatar(
            MagicMock(), MagicMock(), avatar_id, LiveKitSettings(), settings
        )

    @patch("fancall.agent.worker.simli.AvatarSession")
    async def test_simli_used_for_avatar_id(self, simli_session: MagicMock) -> None:
        """avatar_id + Simli key starts a Simli avatar with that face"""
        simli_session.return_value.start = AsyncMock()

        await self._start("face-1", AvatarSettings(simli_api_key="s"))

        config = simli_session.call_args.kwargs["simli_config"]
        self.assertEqual(config.face_id, "face-1")
        simli_session.return_value.start.assert_awaited_once()

    @patch("fancall.agent.worker.simli.AvatarSession")
    async def test_voice_only_without_key(self, simli_session: MagicMock) -> None:
        """No API key means no avatar is started"""
        await self._start("face-1", AvatarSettings(simli_api_key=None))

        simli_session.assert_not_called()

    @patch("fancall.agent.worker.simli.AvatarSession")
    async def test_voice_only_without_avatar_id(self, simli_session: MagicMock) -> None:
        """No avatar_id means no avatar is started"""
        await self._start(None, AvatarSettings(simli_api_key="s"))

        simli_session.assert_not_called()

    @patch("fancall.agent.worker.simli.AvatarSession")
    async def test_start_failure_falls_back_to_voice(
        self, simli_session: MagicMock
    ) -> None:
        """A provider error must not break the call"""
        simli_session.return_value.start = AsyncMock(side_effect=RuntimeError("down"))

        await self._start("face-1", AvatarSettings(simli_api_key="s"))

        simli_session.return_value.start.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
