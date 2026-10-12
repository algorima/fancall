"""
Unit tests for avatar provider selection in the agent worker
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fancall.agent.worker import start_avatar, wait_for_answer
from fancall.settings import AvatarSettings, LiveKitSettings

PICTURE_URL = "https://example.com/idol.png"


class TestStartAvatar(unittest.IsolatedAsyncioTestCase):
    """Test cases for start_avatar"""

    async def _start(
        self,
        avatar_id: str | None,
        profile_picture_url: str | None,
        settings: AvatarSettings,
    ) -> None:
        await start_avatar(
            MagicMock(),
            MagicMock(),
            avatar_id,
            profile_picture_url,
            LiveKitSettings(),
            settings,
        )

    @patch("fancall.agent.worker.lemonslice.AvatarSession")
    @patch("fancall.agent.worker.simli.AvatarSession")
    async def test_simli_used_for_avatar_id(
        self, simli_session: MagicMock, lemonslice_session: MagicMock
    ) -> None:
        """avatar_id + Simli key starts a Simli avatar with that face"""
        simli_session.return_value.start = AsyncMock()
        settings = AvatarSettings(
            tavus_api_key=None, simli_api_key="s", lemonslice_api_key="l"
        )

        await self._start("face-1", PICTURE_URL, settings)

        config = simli_session.call_args.kwargs["simli_config"]
        self.assertEqual(config.face_id, "face-1")
        simli_session.return_value.start.assert_awaited_once()
        lemonslice_session.assert_not_called()

    @patch("fancall.agent.worker.lemonslice.AvatarSession")
    @patch("fancall.agent.worker.simli.AvatarSession")
    async def test_lemonslice_used_for_picture_only(
        self, simli_session: MagicMock, lemonslice_session: MagicMock
    ) -> None:
        """Without avatar_id, the profile picture is animated by LemonSlice"""
        lemonslice_session.return_value.start = AsyncMock()
        settings = AvatarSettings(
            tavus_api_key=None, simli_api_key="s", lemonslice_api_key="l"
        )

        await self._start(None, PICTURE_URL, settings)

        self.assertEqual(
            lemonslice_session.call_args.kwargs["agent_image_url"], PICTURE_URL
        )
        lemonslice_session.return_value.start.assert_awaited_once()
        simli_session.assert_not_called()

    @patch("fancall.agent.worker.lemonslice.AvatarSession")
    @patch("fancall.agent.worker.simli.AvatarSession")
    async def test_voice_only_without_keys(
        self, simli_session: MagicMock, lemonslice_session: MagicMock
    ) -> None:
        """No API key means no avatar is started"""
        settings = AvatarSettings(
            tavus_api_key=None, simli_api_key=None, lemonslice_api_key=None
        )

        await self._start("face-1", PICTURE_URL, settings)

        simli_session.assert_not_called()
        lemonslice_session.assert_not_called()

    @patch("fancall.agent.worker.lemonslice.AvatarSession")
    @patch("fancall.agent.worker.simli.AvatarSession")
    @patch("fancall.agent.worker.tavus.AvatarSession")
    async def test_tavus_preferred_when_configured(
        self,
        tavus_session: MagicMock,
        simli_session: MagicMock,
        lemonslice_session: MagicMock,
    ) -> None:
        """A Tavus key wins over Simli and LemonSlice, using the configured face"""
        tavus_session.return_value.start = AsyncMock()
        settings = AvatarSettings(
            tavus_api_key="t",
            tavus_face_id="face-t",
            simli_api_key="s",
            lemonslice_api_key="l",
        )

        await self._start("face-1", PICTURE_URL, settings)

        self.assertEqual(tavus_session.call_args.kwargs["face_id"], "face-t")
        tavus_session.return_value.start.assert_awaited_once()
        simli_session.assert_not_called()
        lemonslice_session.assert_not_called()

    @patch("fancall.agent.worker.tavus.AvatarSession")
    async def test_tavus_stock_face_when_unset(self, tavus_session: MagicMock) -> None:
        """Without a face id, Tavus falls back to its stock face (NOT_GIVEN)"""
        tavus_session.return_value.start = AsyncMock()
        settings = AvatarSettings(tavus_api_key="t", tavus_face_id=None)

        await self._start(None, None, settings)

        self.assertFalse(tavus_session.call_args.kwargs["face_id"])
        tavus_session.return_value.start.assert_awaited_once()

    @patch("fancall.agent.worker.simli.AvatarSession")
    async def test_start_failure_falls_back_to_voice(
        self, simli_session: MagicMock
    ) -> None:
        """A provider error must not break the call"""
        simli_session.return_value.start = AsyncMock(side_effect=RuntimeError("down"))
        settings = AvatarSettings(tavus_api_key=None, simli_api_key="s")

        await self._start("face-1", None, settings)

        simli_session.return_value.start.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()


class TestWaitForAnswer(unittest.IsolatedAsyncioTestCase):
    """Test cases for wait_for_answer"""

    async def test_returns_true_when_fan_joins(self) -> None:
        """The call proceeds once the fan joins the room"""
        ctx = MagicMock()
        ctx.wait_for_participant = AsyncMock()

        answered = await wait_for_answer(ctx, timeout=1)

        self.assertTrue(answered)
        ctx.shutdown.assert_not_called()

    async def test_shuts_down_when_unanswered(self) -> None:
        """An unanswered call ends the job without starting paid media"""

        async def never_joins() -> None:
            await asyncio.Event().wait()

        ctx = MagicMock()
        ctx.wait_for_participant = never_joins

        answered = await wait_for_answer(ctx, timeout=0.01)

        self.assertFalse(answered)
        ctx.shutdown.assert_called_once()
