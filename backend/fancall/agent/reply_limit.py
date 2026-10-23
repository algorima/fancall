"""
Keep the idol's spoken replies short.

In real video call fansigns an idol speaks about 1.3 seconds at a time. The
prompt asks for short replies, but the LLM sometimes runs on, so the reply
stream is cut after a fixed number of sentences before it reaches TTS.
"""

import re
from collections.abc import AsyncIterable, AsyncIterator
from typing import TypeVar

from livekit.agents import llm

SENTENCE_ENDINGS = frozenset(".?!…")
# "~" often trails an ending ("좋아요?~") but also appears inside words ("진~짜")
TRAILING_MARKS = frozenset("~\"')")

Chunk = TypeVar("Chunk")


async def limit_sentences(
    source: AsyncIterable[Chunk], max_sentences: int
) -> AsyncIterator[Chunk]:
    """
    Pass the reply stream through until `max_sentences` sentences have ended.

    Text chunks (str or llm.ChatChunk content) are cut right after the last
    allowed sentence. A run of endings such as "??" or "!!" counts once. A
    sentence counts as ended when its ending is followed by more text, so a
    reply that stops at the limit is passed through whole.
    """
    ended = 0
    in_ending = False

    async for chunk in source:
        text = _text_of(chunk)
        if not text:
            yield chunk
            continue

        for index, char in enumerate(text):
            if char in SENTENCE_ENDINGS or (in_ending and char in TRAILING_MARKS):
                in_ending = True
                continue
            if in_ending:
                ended += 1
                in_ending = False
                if ended >= max_sentences:
                    kept = text[:index].rstrip()
                    if kept:
                        yield _with_text(chunk, kept)
                    return
        yield chunk


# An interjection at the very start of the LLM's reply, said again right
# after a prepared reaction ("Ooh~ Aww, thank you!", 2026-10-23 call)
_OPENING_INTERJECTION = re.compile(
    r"^\s*((?:aww+|ahh*|wow|ooh+|oh(?!,? really)|hmm+|mm-hm|헐|우와|와|아+|오+|어+|음+)[~!,.]+\s*)+",
    re.IGNORECASE,
)
# Enough of the reply's start to see the whole interjection
_OPENING_CHARS = 16


async def drop_opening_interjection(
    source: AsyncIterable[Chunk],
) -> AsyncIterator[Chunk]:
    """Pass the reply stream through without a leading interjection like "Aww,"."""
    head: Chunk | None = None
    buffered = ""
    async for chunk in source:
        text = _text_of(chunk)
        if text is None or (head is not None and len(buffered) >= _OPENING_CHARS):
            yield chunk
            continue
        if head is None:
            head = chunk
        buffered += text
        if len(buffered) >= _OPENING_CHARS:
            yield _with_text(head, _strip_interjection(buffered))
    if head is not None and len(buffered) < _OPENING_CHARS:
        rest = _strip_interjection(buffered)
        if rest.strip():
            yield _with_text(head, rest)


def _strip_interjection(text: str) -> str:
    rest = _OPENING_INTERJECTION.sub("", text, count=1)
    return rest[:1].upper() + rest[1:]


def _text_of(chunk: object) -> str | None:
    if isinstance(chunk, str):
        return chunk
    if isinstance(chunk, llm.ChatChunk) and chunk.delta is not None:
        return chunk.delta.content
    return None


def _with_text(chunk: Chunk, text: str) -> Chunk:
    if isinstance(chunk, llm.ChatChunk):
        assert chunk.delta is not None
        delta = chunk.delta.model_copy(update={"content": text})
        return chunk.model_copy(update={"delta": delta})  # type: ignore[return-value]
    return text  # type: ignore[return-value]
