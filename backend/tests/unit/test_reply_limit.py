"""
Unit tests for the reply limiter that keeps spoken replies short
"""

import unittest
from collections.abc import AsyncIterator

from livekit.agents import llm

from fancall.agent.reply_limit import drop_opening_interjection, limit_sentences


async def stream(*pieces: str) -> AsyncIterator[str]:
    for piece in pieces:
        yield piece


async def collect(source, max_sentences: int) -> str:
    out = []
    async for chunk in limit_sentences(source, max_sentences):
        if isinstance(chunk, str):
            out.append(chunk)
        else:
            assert chunk.delta is not None
            out.append(chunk.delta.content or "")
    return "".join(out)


class TestLimitSentences(unittest.IsolatedAsyncioTestCase):
    """Tests for limit_sentences"""

    async def test_keeps_reply_within_limit(self):
        text = await collect(stream("진짜요? ", "영광이에요!"), max_sentences=2)
        self.assertEqual(text, "진짜요? 영광이에요!")

    async def test_cuts_after_limit(self):
        text = await collect(
            stream("진짜요? 영광영광! ", "어떻게 왔어요? 저는 오늘 연습했어요."),
            max_sentences=2,
        )
        self.assertEqual(text, "진짜요? 영광영광!")

    async def test_cuts_across_chunk_boundaries(self):
        text = await collect(stream("시험 ", "잘 봤어", "요?", " 고생했", "어요."), 1)
        self.assertEqual(text, "시험 잘 봤어요?")

    async def test_repeated_punctuation_ends_one_sentence(self):
        text = await collect(stream("언제?? ", "대박!! ", "또 봐요."), max_sentences=2)
        self.assertEqual(text, "언제?? 대박!!")

    async def test_tilde_does_not_end_sentence(self):
        text = await collect(stream("진~짜 처음이에요~? ", "반가워요."), 1)
        self.assertEqual(text, "진~짜 처음이에요~?")

    async def test_reply_without_punctuation_passes_through(self):
        text = await collect(stream("안녕 반가워"), max_sentences=1)
        self.assertEqual(text, "안녕 반가워")

    async def test_limits_chat_chunks(self):
        async def chunks():
            for piece in ("고마워요. ", "근데 ", "진짜요?"):
                yield llm.ChatChunk(id="1", delta=llm.ChoiceDelta(content=piece))

        text = await collect(chunks(), max_sentences=1)
        self.assertEqual(text, "고마워요.")


async def dropped(*pieces: str) -> str:
    out = []
    async for chunk in drop_opening_interjection(stream(*pieces)):
        out.append(chunk)
    return "".join(out)


class DropOpeningInterjectionTest(unittest.IsolatedAsyncioTestCase):
    async def test_drops_a_repeated_interjection(self):
        self.assertEqual(
            await dropped("Aww, thank you! ", "I'll work hard."),
            "Thank you! I'll work hard.",
        )

    async def test_keeps_oh_really(self):
        self.assertEqual(
            await dropped("Oh, really? Okay, here goes!"),
            "Oh, really? Okay, here goes!",
        )

    async def test_korean_interjection(self):
        self.assertEqual(
            await dropped("아~ ", "시험 진짜 힘들었겠다"), "시험 진짜 힘들었겠다"
        )

    async def test_short_reply(self):
        self.assertEqual(await dropped("Wow! ", "Yes."), "Yes.")

    async def test_chat_chunks(self):
        async def chunks():
            for piece in ("Ooh~ ", "Thank you so much!"):
                yield llm.ChatChunk(id="1", delta=llm.ChoiceDelta(content=piece))

        out = []
        async for chunk in drop_opening_interjection(chunks()):
            assert chunk.delta is not None
            out.append(chunk.delta.content or "")
        self.assertEqual("".join(out), "Thank you so much!")


if __name__ == "__main__":
    unittest.main()
