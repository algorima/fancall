"""LiveKit Cloud TTS 설정(목소리·언어·말투 지시문)이 inference.TTS 인자로 옮겨지는지."""

import unittest

from fancall.agent.cloud_tts import cloud_tts_kwargs
from fancall.settings import FancallModelSettings


class CloudTtsKwargsTest(unittest.TestCase):
    def test_model_only(self) -> None:
        settings = FancallModelSettings(tts_model="fishaudio/s2.1-pro:abc")
        self.assertEqual(
            cloud_tts_kwargs(settings), {"model": "fishaudio/s2.1-pro:abc"}
        )

    def test_language_and_instructions(self) -> None:
        settings = FancallModelSettings(
            tts_model="google/gemini-3.8-flash-tts:Puck",
            tts_language="ko",
            tts_instructions="차분하고 다정하게",
        )
        kwargs = cloud_tts_kwargs(settings)
        self.assertEqual(kwargs["model"], "google/gemini-3.8-flash-tts:Puck")
        self.assertEqual(kwargs["language"], "ko")
        self.assertEqual(kwargs["extra_kwargs"], {"instructions": "차분하고 다정하게"})

    def test_blank_instructions_are_dropped(self) -> None:
        settings = FancallModelSettings(
            tts_model="inworld/inworld-tts-2:Ashley", tts_instructions="  "
        )
        self.assertNotIn("extra_kwargs", cloud_tts_kwargs(settings))


if __name__ == "__main__":
    unittest.main()
