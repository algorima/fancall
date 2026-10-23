"""
A short reaction the trainee says the moment the fan finishes speaking.

In real 영통팬싸 the next person starts talking about 1.4s after the other
stops (median of 295 calls, docs/call-naturalness-criteria.md). Our full reply
waits for the LLM's first token, so a reaction prepared in advance opens the
reply the way idols do ("아 진짜요?", "오~"), and the real reply follows it.

Which reactions and how often come from the same calls: of 385 idol replies
that directly follow a fan's line, 122 (31.7%) open with one of the 15
reactions below. The counts are those openings. English and Japanese are
translations of the Korean ones, not measured.
"""

import hashlib
import logging
import random
import re
from collections.abc import AsyncIterable, AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TypeVar

import aiohttp
from livekit import rtc
from livekit.agents.tts import TTS

logger = logging.getLogger(__name__)

T = TypeVar("T")


class FanLine(Enum):
    """What the fan just said, as far as choosing a reaction goes."""

    QUESTION = "question"
    COMPLIMENT = "compliment"
    STATEMENT = "statement"


Q, C, S = FanLine.QUESTION, FanLine.COMPLIMENT, FanLine.STATEMENT


@dataclass(frozen=True)
class Reaction:
    """One reaction, how often idols opened with it, and after what it fits."""

    ko: str
    en: str
    ja: str
    count: int
    fits: frozenset[FanLine]


# Openings of idol replies in real 영통팬싸 (2026-10-23 count, 385 replies).
# fits leaves out only clear mismatches, like thanking someone for a question.
REACTIONS: tuple[Reaction, ...] = (
    Reaction("아~", "Ah~", "あ~", 21, frozenset({Q, C, S})),
    Reaction("아 진짜요?", "Oh, really?", "えっ、ほんと？", 19, frozenset({C, S})),
    Reaction("네~", "Yeah~", "うん~", 13, frozenset({Q, S})),
    Reaction("어~", "Ohh~", "えー", 12, frozenset({Q, S})),
    Reaction("아니~", "Aww, no~", "いやいや~", 10, frozenset({C})),
    Reaction("오~", "Ooh~", "おお~", 8, frozenset({Q, C, S})),
    Reaction("고마워요", "Aww, thank you", "ありがとう", 7, frozenset({C})),
    Reaction("우와", "Wow", "わあ", 7, frozenset({C, S})),
    Reaction("맞아요", "Right!", "そうそう", 7, frozenset({S})),
    Reaction("오케이", "Okay!", "オッケー", 5, frozenset({Q, S})),
    Reaction("응응", "Mm-hm", "うんうん", 4, frozenset({Q, S})),
    Reaction("어?", "Huh?", "え？", 3, frozenset({Q, S})),
    Reaction("음~", "Hmm~", "うーん", 2, frozenset({Q, S})),
    Reaction("아유", "Aww", "あらら", 2, frozenset({C})),
    Reaction("대박", "No way!", "やばい", 2, frozenset({C, S})),
)


# How the trainee picks the talk back up after a pause, before the new line.
# Said from prepared audio, so the nudge can wait longer for the fan and still
# be heard within 3s of silence.
@dataclass(frozen=True)
class Fillers:
    """Fillers in each language."""

    ko: tuple[str, ...]
    en: tuple[str, ...]
    ja: tuple[str, ...]


FILLERS = Fillers(
    ko=("음~", "아 맞다~", "근데~", "아 그리고~"),
    en=("Hmm~", "Oh, right~", "So~", "Oh, and~"),
    ja=("うーん", "あ、そうだ", "ねえ~", "あとね~"),
)

# Share of idol replies to a fan that open with a reaction (122 / 385)
REACTION_RATE = 0.317

_COMPLIMENT = re.compile(
    r"잘생|예쁘|이쁘|귀여|멋있|멋져|사랑|좋아해|최고|응원|화이팅|파이팅|보고\s?싶"
    r"|love|cute|handsome|pretty|cool|amazing|the best|proud|miss you"
    r"|好き|かわい|かっこい|最高|応援",
    re.IGNORECASE,
)
_QUESTION = re.compile(
    r"[?？]\s*$|^(what|why|how|when|where|who|which|do|did|are|is|can|will|have)\b"
    r"|(뭐|어디|언제|왜|어떻게|누구|몇)",
    re.IGNORECASE,
)


def is_question(fan_text: str) -> bool:
    """Whether the fan's line asks something."""
    return bool(_QUESTION.search(fan_text.strip()))


def classify(fan_text: str) -> FanLine:
    """Rough kind of the fan's line; a compliment wins over a question."""
    text = fan_text.strip()
    if _COMPLIMENT.search(text):
        return FanLine.COMPLIMENT
    if is_question(text):
        return FanLine.QUESTION
    return FanLine.STATEMENT


class QuickReactions:
    """Picks reactions in the fan's language at the rates real idols use them."""

    def __init__(
        self,
        language: str | None,
        rate: float = REACTION_RATE,
        rng: random.Random | None = None,
    ):
        lang = (language or "en")[:2]
        self._lang = lang if lang in {"ko", "en", "ja"} else "en"
        self._rate = rate
        self._rng = rng or random.Random()
        self._last: str | None = None
        self._fillers: tuple[str, ...] = getattr(FILLERS, self._lang)

    def _text(self, reaction: Reaction) -> str:
        return str(getattr(reaction, self._lang))

    @property
    def words(self) -> tuple[str, ...]:
        """All reactions and fillers for this language."""
        return tuple(self._text(r) for r in REACTIONS) + self._fillers

    def filler(self) -> str:
        """A filler for picking the talk back up, never the same twice in a row."""
        choices = [f for f in self._fillers if f != self._last]
        self._last = self._rng.choice(choices)
        return self._last

    def pick(self, fan_text: str) -> str | None:
        """A reaction for the fan's line, or None when this reply opens without one.

        Never the same reaction twice in a row.
        """
        if self._rng.random() >= self._rate:
            return None
        kind = classify(fan_text)
        choices = [
            r for r in REACTIONS if kind in r.fits and self._text(r) != self._last
        ]
        reaction = self._rng.choices(choices, weights=[r.count for r in choices])[0]
        self._last = self._text(reaction)
        return self._last


ReactionFetch = Callable[[str], Awaitable[bytes]]

# Default rate for prerendered reactions; the worker uses its TTS's rate so
# the reaction and the reply that follows it share one audio stream
REACTION_SAMPLE_RATE = 24000


def pcm_to_frames(
    pcm: bytes, sample_rate: int, frame_ms: int = 20
) -> list[rtc.AudioFrame]:
    """Split 16-bit mono PCM into audio frames for the agent's audio output."""
    step = sample_rate * frame_ms // 1000 * 2
    return [
        rtc.AudioFrame(
            data=pcm[i : i + step],
            sample_rate=sample_rate,
            num_channels=1,
            samples_per_channel=len(pcm[i : i + step]) // 2,
        )
        for i in range(0, len(pcm), step)
    ]


async def prerender(
    fetch: ReactionFetch, words: tuple[str, ...], sample_rate: int
) -> dict[str, list[rtc.AudioFrame]]:
    """Synthesize each reaction once so playing it later skips TTS.

    A word whose synthesis fails is left out; it is then spoken through TTS live.
    """
    cache: dict[str, list[rtc.AudioFrame]] = {}
    for word in words:
        try:
            pcm = await fetch(word)
        except Exception:  # pylint: disable=broad-exception-caught
            logger.warning("Could not prerender reaction %r; will use live TTS", word)
            continue
        if pcm:
            cache[word] = pcm_to_frames(pcm, sample_rate)
    return cache


def elevenlabs_pcm_fetch(
    api_key: str, voice_id: str, model: str, sample_rate: int
) -> ReactionFetch:
    """Fetch raw PCM for a word from the ElevenLabs REST API.

    The LiveKit ElevenLabs plugin crashed the job process (exit -11) when asked
    to synthesize these words while the session was starting, so this goes to
    the REST endpoint directly.
    """

    async def fetch(word: str) -> bytes:
        async with aiohttp.ClientSession() as http:
            async with http.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                params={"output_format": f"pcm_{sample_rate}"},
                headers={"xi-api-key": api_key},
                json={"text": word, "model_id": model},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                response.raise_for_status()
                return await response.read()

    return fetch


def cached_fetch(
    fetch: ReactionFetch,
    directory: Path,
    key: str,
    before_fetch: Callable[[], Awaitable[None]] | None = None,
) -> ReactionFetch:
    """Keep fetched PCM on disk, so each voice pays for each line only once.

    key names the voice and format (model, voice id, sample rate).
    before_fetch runs before synthesizing a line that is not on disk yet; the
    worker uses it to wait until the call is idle, since the TTS service
    queued the live reply behind these lines (8s, 2026-10-23).
    """

    async def cached(word: str) -> bytes:
        path = directory / f"{hashlib.sha1(f'{key}|{word}'.encode()).hexdigest()}.pcm"
        if path.exists():
            return path.read_bytes()
        if before_fetch is not None:
            await before_fetch()
        pcm = await fetch(word)
        if pcm:
            directory.mkdir(parents=True, exist_ok=True)
            path.write_bytes(pcm)
        return pcm

    return cached


def tts_pcm_fetch(tts: TTS) -> ReactionFetch:
    """Fetch raw PCM for a word through any LiveKit TTS (e.g. LiveKit Cloud).

    The PCM is at tts.sample_rate, mono.
    """

    async def fetch(word: str) -> bytes:
        async with tts.synthesize(word) as stream:
            return b"".join([bytes(audio.frame.data) async for audio in stream])

    return fetch


async def prepend(head: list[T], rest: AsyncIterable[T]) -> AsyncIterator[T]:
    """Yield head first, then everything from rest."""
    for item in head:
        yield item
    async for item in rest:
        yield item


async def strip_prefix(text: AsyncIterable[str], prefix: str) -> AsyncIterator[str]:
    """Pass a text stream through without its leading prefix.

    Used for the reaction at the start of a reply: it is already spoken from
    prepared audio, so the TTS must not say it again.
    """
    buffered = ""
    stripped = False
    async for chunk in text:
        if stripped:
            yield chunk
            continue
        buffered += chunk
        head = buffered.lstrip()
        if len(head) < len(prefix) and prefix.startswith(head):
            continue
        if head.startswith(prefix):
            head = head[len(prefix) :].lstrip()
        stripped = True
        if head:
            yield head
    if not stripped and buffered.strip() and buffered.strip() != prefix:
        yield buffered
