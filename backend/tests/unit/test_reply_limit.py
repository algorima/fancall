"""
Unit tests for the reply limiter that keeps spoken replies short
"""

import unittest
from collections.abc import AsyncIterator

from livekit.agents import llm

from fancall.agent.reply_limit import limit_sentences


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

    async def test_ellipsis_and_double_dots_are_pauses(self):
        text = await collect(stream("와.. 진짜? 대박이다! 또 봐요."), max_sentences=2)
        self.assertEqual(text, "와.. 진짜? 대박이다!")
        text = await collect(stream("음… 그래요? 좋아요! 또 봐요."), max_sentences=2)
        self.assertEqual(text, "음… 그래요? 좋아요!")
        text = await collect(
            stream("글쎄... 몰라요. 그냥 그래요. 또요."), max_sentences=2
        )
        self.assertEqual(text, "글쎄... 몰라요. 그냥 그래요.")

    async def test_decimal_point_is_not_an_ending(self):
        text = await collect(stream("3.5점이에요. 진짜요. 또요."), max_sentences=2)
        self.assertEqual(text, "3.5점이에요. 진짜요.")

    async def test_decimal_point_split_across_chunks(self):
        text = await collect(stream("3.", "5점이에요. 진짜요. 또요."), max_sentences=2)
        self.assertEqual(text, "3.5점이에요. 진짜요.")

    async def test_fullwidth_endings_count(self):
        text = await collect(stream("本当？ すごい！ またね。"), max_sentences=2)
        self.assertEqual(text, "本当？ すごい！")
        text = await collect(stream("你好。你好吗？我很好！"), max_sentences=2)
        self.assertEqual(text, "你好。你好吗？")

    async def test_reply_without_punctuation_passes_through(self):
        text = await collect(stream("안녕 반가워"), max_sentences=1)
        self.assertEqual(text, "안녕 반가워")

    async def test_limits_chat_chunks(self):
        async def chunks():
            for piece in ("고마워요. ", "근데 ", "진짜요?"):
                yield llm.ChatChunk(id="1", delta=llm.ChoiceDelta(content=piece))

        text = await collect(chunks(), max_sentences=1)
        self.assertEqual(text, "고마워요.")


if __name__ == "__main__":
    unittest.main()
