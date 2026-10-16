"""
Unit tests for avatar provider selection in the agent worker
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fancall.agent.worker import start_avatar
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
            anam_api_key=None,
            tavus_api_key=None,
            simli_api_key="s",
            lemonslice_api_key="l",
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
            anam_api_key=None,
            tavus_api_key=None,
            simli_api_key="s",
            lemonslice_api_key="l",
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
            anam_api_key=None,
            tavus_api_key=None,
            simli_api_key=None,
            lemonslice_api_key=None,
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
            anam_api_key=None,
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

    @patch("fancall.agent.worker.simli.AvatarSession")
    @patch("fancall.agent.worker.tavus.AvatarSession")
    @patch("fancall.agent.worker.anam.AvatarSession")
    async def test_anam_preferred_when_configured(
        self,
        anam_session: MagicMock,
        tavus_session: MagicMock,
        simli_session: MagicMock,
    ) -> None:
        """Anam key + avatar wins over Tavus and Simli, rendering portrait video"""
        anam_session.return_value.start = AsyncMock()
        settings = AvatarSettings(
            anam_api_key="a",
            anam_avatar_id="avatar-a",
            tavus_api_key="t",
            simli_api_key="s",
        )

        await self._start("face-1", PICTURE_URL, settings)

        kwargs = anam_session.call_args.kwargs
        self.assertEqual(kwargs["persona_config"].avatarId, "avatar-a")
        self.assertEqual(
            (
                kwargs["session_options"].video_width,
                kwargs["session_options"].video_height,
            ),
            (768, 1152),
        )
        anam_session.return_value.start.assert_awaited_once()
        tavus_session.assert_not_called()
        simli_session.assert_not_called()

    @patch("fancall.agent.worker.tavus.AvatarSession")
    @patch("fancall.agent.worker.anam.AvatarSession")
    async def test_anam_skipped_without_avatar_id(
        self, anam_session: MagicMock, tavus_session: MagicMock
    ) -> None:
        """An Anam key alone is not enough; the next provider is used"""
        tavus_session.return_value.start = AsyncMock()
        settings = AvatarSettings(
            anam_api_key="a", anam_avatar_id=None, tavus_api_key="t"
        )

        await self._start(None, None, settings)

        anam_session.assert_not_called()
        tavus_session.return_value.start.assert_awaited_once()

    @patch("fancall.agent.worker.tavus.AvatarSession")
    async def test_tavus_stock_face_when_unset(self, tavus_session: MagicMock) -> None:
        """Without a face id, Tavus falls back to its stock face (NOT_GIVEN)"""
        tavus_session.return_value.start = AsyncMock()
        settings = AvatarSettings(
            anam_api_key=None, tavus_api_key="t", tavus_face_id=None
        )

        await self._start(None, None, settings)

        self.assertFalse(tavus_session.call_args.kwargs["face_id"])
        tavus_session.return_value.start.assert_awaited_once()

    @patch("fancall.agent.worker.simli.AvatarSession")
    async def test_start_failure_falls_back_to_voice(
        self, simli_session: MagicMock
    ) -> None:
        """A provider error must not break the call"""
        simli_session.return_value.start = AsyncMock(side_effect=RuntimeError("down"))
        settings = AvatarSettings(
            anam_api_key=None, tavus_api_key=None, simli_api_key="s"
        )

        await self._start("face-1", None, settings)

        simli_session.return_value.start.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
