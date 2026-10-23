"""
Unit tests for the short reaction played as soon as the fan finishes speaking
"""

import random
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from fancall.agent.quick_reaction import (
    FILLERS,
    REACTIONS,
    FanLine,
    QuickReactions,
    cached_fetch,
    classify,
    pcm_to_frames,
    prepend,
    prerender,
    strip_prefix,
)

SAMPLE_RATE = 24000


class ClassifyTest(unittest.TestCase):
    def test_kinds(self):
        self.assertEqual(classify("What did you practice today?"), FanLine.QUESTION)
        self.assertEqual(classify("오늘 뭐 했어요"), FanLine.QUESTION)
        self.assertEqual(classify("You're so cute"), FanLine.COMPLIMENT)
        self.assertEqual(classify("오빠 사랑해요?"), FanLine.COMPLIMENT)
        self.assertEqual(classify("I had an exam today."), FanLine.STATEMENT)


class QuickReactionsTest(unittest.TestCase):
    def test_uses_the_fans_language(self):
        ko = QuickReactions("ko", rate=1.0).pick("시험 봤어요")
        en = QuickReactions("en", rate=1.0).pick("I had an exam")
        self.assertIn(ko, [r.ko for r in REACTIONS])
        self.assertIn(en, [r.en for r in REACTIONS])

    def test_unknown_language_falls_back_to_english(self):
        self.assertEqual(QuickReactions("xx").words, QuickReactions("en").words)
        self.assertEqual(QuickReactions(None).words, QuickReactions("en").words)

    def test_reacts_at_the_given_rate(self):
        reactions = QuickReactions("ko", rate=0.317, rng=random.Random(0))
        picked = [reactions.pick("시험 봤어요") for _ in range(2000)]
        share = sum(p is not None for p in picked) / len(picked)
        self.assertAlmostEqual(share, 0.317, delta=0.03)

    def test_follows_the_measured_shares(self):
        reactions = QuickReactions("ko", rate=1.0, rng=random.Random(0))
        picked = Counter(reactions.pick("시험 봤어요") for _ in range(4000))
        # 이야기 뒤에는 "아~"(21)가 "대박"(2)보다 훨씬 자주 나온다
        self.assertGreater(picked["아~"], picked["대박"] * 4)

    def test_never_thanks_for_a_question(self):
        reactions = QuickReactions("ko", rate=1.0, rng=random.Random(0))
        picked = {reactions.pick("오늘 뭐 연습했어요?") for _ in range(500)}
        self.assertNotIn("고마워요", picked)
        self.assertNotIn("아 진짜요?", picked)

    def test_fillers_in_the_fans_language(self):
        reactions = QuickReactions("ko", rng=random.Random(0))
        fillers = [reactions.filler() for _ in range(10)]
        self.assertTrue(set(fillers) <= set(FILLERS.ko))
        for prev, cur in zip(fillers, fillers[1:]):
            self.assertNotEqual(prev, cur)
        self.assertTrue(set(FILLERS.ko) <= set(reactions.words))

    def test_does_not_repeat_the_same_reaction_twice_in_a_row(self):
        reactions = QuickReactions("en", rate=1.0, rng=random.Random(1))
        words = [reactions.pick("I had an exam") for _ in range(50)]
        for prev, cur in zip(words, words[1:]):
            self.assertNotEqual(prev, cur)


class CachedFetchTest(unittest.IsolatedAsyncioTestCase):
    async def test_fetches_each_line_once(self):
        calls = []

        async def fetch(word: str) -> bytes:
            calls.append(word)
            return b"\x01\x00"

        with tempfile.TemporaryDirectory() as tmp:
            cached = cached_fetch(fetch, Path(tmp), "voice-a:24000")
            self.assertEqual(await cached("Oh~"), b"\x01\x00")
            self.assertEqual(await cached("Oh~"), b"\x01\x00")
            other_voice = cached_fetch(fetch, Path(tmp), "voice-b:24000")
            await other_voice("Oh~")

        self.assertEqual(calls, ["Oh~", "Oh~"])

    async def test_waits_before_synthesizing_only(self):
        waits = []

        async def fetch(_word: str) -> bytes:
            return b"\x01\x00"

        async def before() -> None:
            waits.append(1)

        with tempfile.TemporaryDirectory() as tmp:
            cached = cached_fetch(fetch, Path(tmp), "v", before_fetch=before)
            await cached("Oh~")
            await cached("Oh~")

        self.assertEqual(waits, [1])


async def collect(stream):
    return [item async for item in stream]


async def chunks(*items):
    for item in items:
        yield item


class StreamHelpersTest(unittest.IsolatedAsyncioTestCase):
    async def test_prepend(self):
        self.assertEqual(await collect(prepend([1, 2], chunks(3))), [1, 2, 3])

    async def test_strip_prefix_across_chunks(self):
        stream = strip_prefix(chunks("Oh, ", "really? I", " practiced."), "Oh, really?")
        self.assertEqual("".join(await collect(stream)), "I practiced.")

    async def test_strip_prefix_leaves_other_text(self):
        stream = strip_prefix(chunks("Hello there"), "Oh~")
        self.assertEqual("".join(await collect(stream)), "Hello there")

    async def test_strip_prefix_only_prefix(self):
        self.assertEqual(await collect(strip_prefix(chunks("Oh~ "), "Oh~")), [])


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
        self.assertEqual(len(cache["Oh~"]), 1)


if __name__ == "__main__":
    unittest.main()
