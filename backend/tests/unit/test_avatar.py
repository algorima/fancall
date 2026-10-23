"""
Unit tests for Simli avatar startup in the agent worker
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp

from fancall.agent.worker import start_avatar
from fancall.settings import FancallCallSettings, LiveKitSettings, SimliSettings


class TestSimliSettings(unittest.TestCase):
    """Test cases for SimliSettings"""

    @patch.dict("os.environ", {"SIMLI_API_KEY": "from-env"})
    def test_reads_simli_api_key(self) -> None:
        """The key comes from SIMLI_API_KEY like other service settings"""
        self.assertEqual(SimliSettings().api_key, "from-env")


class TestStartAvatar(unittest.IsolatedAsyncioTestCase):
    """Test cases for start_avatar"""

    async def _start(
        self,
        avatar_id: str | None,
        settings: SimliSettings,
        call_settings: FancallCallSettings | None = None,
    ) -> None:
        await start_avatar(
            MagicMock(),
            MagicMock(),
            avatar_id,
            LiveKitSettings(),
            settings,
            call_settings or FancallCallSettings(),
        )

    @patch("fancall.agent.worker.simli.AvatarSession")
    async def test_simli_used_for_avatar_id(self, simli_session: MagicMock) -> None:
        """avatar_id + Simli key starts a Simli avatar with that face"""
        simli_session.return_value.start = AsyncMock()

        await self._start("face-1", SimliSettings(api_key="s"))

        config = simli_session.call_args.kwargs["simli_config"]
        self.assertEqual(config.face_id, "face-1")
        simli_session.return_value.start.assert_awaited_once()

    @patch("fancall.agent.worker.simli.AvatarSession")
    async def test_avatar_stays_for_whole_call(self, simli_session: MagicMock) -> None:
        """Simli must not disconnect before the call (and its goodbye) ends"""
        simli_session.return_value.start = AsyncMock()

        await self._start(
            "face-1",
            SimliSettings(api_key="s"),
            FancallCallSettings(call_duration_seconds=180, closing_grace_seconds=5),
        )

        config = simli_session.call_args.kwargs["simli_config"]
        self.assertEqual(config.max_session_length, 185)
        self.assertEqual(config.max_idle_time, 185)

    @patch("fancall.agent.worker.simli.AvatarSession")
    async def test_voice_only_without_key(self, simli_session: MagicMock) -> None:
        """No API key means no avatar is started"""
        await self._start("face-1", SimliSettings(api_key=None))

        simli_session.assert_not_called()

    @patch("fancall.agent.worker.simli.AvatarSession")
    async def test_voice_only_without_avatar_id(self, simli_session: MagicMock) -> None:
        """No avatar_id means no avatar is started"""
        await self._start(None, SimliSettings(api_key="s"))

        simli_session.assert_not_called()

    @patch("fancall.agent.worker.simli.AvatarSession")
    async def test_simli_http_error_falls_back_to_voice(
        self, simli_session: MagicMock
    ) -> None:
        """A Simli API error status must not break the call"""
        simli_session.return_value.start = AsyncMock(
            side_effect=aiohttp.ClientResponseError(MagicMock(), (), status=500)
        )

        await self._start("face-1", SimliSettings(api_key="s"))

        simli_session.return_value.start.assert_awaited_once()

    @patch("fancall.agent.worker.simli.AvatarSession")
    async def test_network_error_falls_back_to_voice(
        self, simli_session: MagicMock
    ) -> None:
        """A network error reaching Simli must not break the call"""
        simli_session.return_value.start = AsyncMock(
            side_effect=aiohttp.ClientConnectionError("down")
        )

        await self._start("face-1", SimliSettings(api_key="s"))

        simli_session.return_value.start.assert_awaited_once()

    @patch("fancall.agent.worker.simli.AvatarSession")
    async def test_timeout_falls_back_to_voice(self, simli_session: MagicMock) -> None:
        """A Simli timeout must not break the call"""
        simli_session.return_value.start = AsyncMock(side_effect=asyncio.TimeoutError)

        await self._start("face-1", SimliSettings(api_key="s"))

        simli_session.return_value.start.assert_awaited_once()

    @patch("fancall.agent.worker.simli.AvatarSession")
    async def test_unexpected_error_is_raised(self, simli_session: MagicMock) -> None:
        """Configuration or code errors surface instead of being swallowed"""
        simli_session.return_value.start = AsyncMock(
            side_effect=TypeError("unexpected keyword argument")
        )

        with self.assertRaises(TypeError):
            await self._start("face-1", SimliSettings(api_key="s"))


if __name__ == "__main__":
    unittest.main()
