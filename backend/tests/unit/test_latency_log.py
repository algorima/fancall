"""
Unit tests for latency log lines
"""

import unittest
from types import SimpleNamespace

from fancall.agent.latency_log import format_latency


class FormatLatencyTest(unittest.TestCase):
    def test_end_of_turn(self):
        m = SimpleNamespace(
            type="eou_metrics", end_of_utterance_delay=0.42, transcription_delay=0.1
        )
        self.assertEqual(format_latency(m), "LAT end_of_turn=0.42s transcript=0.10s")

    def test_llm_and_tts(self):
        self.assertEqual(
            format_latency(SimpleNamespace(type="llm_metrics", ttft=0.81)),
            "LAT llm_first_token=0.81s",
        )
        self.assertEqual(
            format_latency(SimpleNamespace(type="tts_metrics", ttfb=0.3)),
            "LAT tts_first_audio=0.30s",
        )

    def test_avatar_only_when_measured(self):
        self.assertIsNone(
            format_latency(SimpleNamespace(type="avatar_metrics", playback_latency=0))
        )
        self.assertEqual(
            format_latency(
                SimpleNamespace(type="avatar_metrics", playback_latency=0.25)
            ),
            "LAT avatar_playback=0.25s",
        )

    def test_ignores_other_metrics(self):
        self.assertIsNone(format_latency(SimpleNamespace(type="vad_metrics")))


if __name__ == "__main__":
    unittest.main()
