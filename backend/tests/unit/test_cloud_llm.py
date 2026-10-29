"""LiveKit Inference LLM(예: Gemma) 설정과, 지난 통화 기록을 먼저 꺼내는 프롬프트 줄."""

import os
import unittest
from unittest import mock

from livekit.agents import inference
from livekit.agents.llm import FallbackAdapter

from fancall.agent.cloud_llm import build_llm
from fancall.prompts import memory_note
from fancall.settings import FancallModelSettings

LIVEKIT_ENV = {
    "LIVEKIT_URL": "wss://test.livekit.cloud",
    "LIVEKIT_API_KEY": "key",
    "LIVEKIT_API_SECRET": "secret",
    "OPENAI_API_KEY": "test",
}


@mock.patch.dict(os.environ, LIVEKIT_ENV)
class BuildLlmTest(unittest.TestCase):
    def test_inference_model_is_used_when_set(self) -> None:
        settings = FancallModelSettings(
            llm_inference_model="google/gemma-4-31b-it", openai_fallback_model=""
        )
        llm = build_llm(settings)
        self.assertIsInstance(llm, inference.LLM)
        self.assertEqual(llm.model, "google/gemma-4-31b-it")

    def test_inference_model_keeps_openai_fallback(self) -> None:
        settings = FancallModelSettings(
            llm_inference_model="google/gemma-4-31b-it",
            openai_fallback_model="gpt-4o-mini",
        )
        self.assertIsInstance(build_llm(settings), FallbackAdapter)

    def test_without_inference_model_uses_openai(self) -> None:
        settings = FancallModelSettings(
            llm_inference_model="", openai_fallback_model="", openai_api_key="x"
        )
        self.assertNotIsInstance(build_llm(settings), inference.LLM)


class MemoryNoteTest(unittest.TestCase):
    def test_asks_about_a_remembered_thing_right_after_greeting(self) -> None:
        note = memory_note([("fan", "내일 수학 시험이야"), ("idol", "잘 봐!")])
        self.assertIn("인사 바로 뒤에", note)


if __name__ == "__main__":
    unittest.main()
