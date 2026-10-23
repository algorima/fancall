"""
Unit tests for the short reaction played as soon as the fan finishes speaking
"""

import unittest

from fancall.agent.quick_reaction import (
    QuickReactions,
    pcm_to_frames,
    prerender,
    replay,
)

SAMPLE_RATE = 24000


class QuickReactionsTest(unittest.TestCase):
    def test_uses_the_fans_language(self):
        self.assertIn(QuickReactions("ko").next(), QuickReactions.WORDS["ko"])
        self.assertIn(QuickReactions("en").next(), QuickReactions.WORDS["en"])

    def test_unknown_language_falls_back_to_english(self):
        self.assertIn(QuickReactions("xx").next(), QuickReactions.WORDS["en"])
        self.assertIn(QuickReactions(None).next(), QuickReactions.WORDS["en"])

    def test_does_not_repeat_the_same_word_twice_in_a_row(self):
        reactions = QuickReactions("en")
        words = [reactions.next() for _ in range(20)]
        for prev, cur in zip(words, words[1:]):
            self.assertNotEqual(prev, cur)


class PcmToFramesTest(unittest.TestCase):
    def test_splits_into_20ms_frames(self):
        # 50ms of 16-bit mono audio → 20ms + 20ms + 10ms
        pcm = b"\x00\x00" * (SAMPLE_RATE * 50 // 1000)
        frames = pcm_to_frames(pcm, SAMPLE_RATE)

        self.assertEqual(
            [f.samples_per_channel for f in frames],
            [480, 480, 240],
        )
        self.assertEqual(frames[0].sample_rate, SAMPLE_RATE)


class PrerenderTest(unittest.IsolatedAsyncioTestCase):
    async def test_caches_frames_and_skips_failures(self):
        async def fetch(word: str) -> bytes:
            if word == "bad":
                raise RuntimeError("tts down")
            return b"\x00\x00" * 480

        cache = await prerender(fetch, ("Oh~", "bad"), SAMPLE_RATE)

        self.assertEqual(list(cache), ["Oh~"])
        self.assertEqual(len([f async for f in replay(cache["Oh~"])]), 1)


if __name__ == "__main__":
    unittest.main()
