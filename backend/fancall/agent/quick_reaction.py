"""
A short reaction the trainee says the moment the fan finishes speaking.

In real 영통팬싸 the next person starts talking about 1.4s after the other
stops (median of 295 calls, docs/call-naturalness-criteria.md), and idols
often open with a short backchannel ("아 진짜요?", "오?"). Our full reply waits
for the LLM's first token (about 1.1s on top of end-of-turn, TTS and avatar).
Saying a one-word reaction right away fills that gap the way a person does;
the real reply follows it.
"""

import logging
import random
from collections.abc import AsyncIterator, Awaitable, Callable

import aiohttp
from livekit import rtc

logger = logging.getLogger(__name__)


class QuickReactions:
    """Picks a short backchannel in the fan's language, never the same twice in a row."""

    WORDS: dict[str, tuple[str, ...]] = {
        "en": ("Oh~", "Hmm~", "Ah~", "Ooh", "Mm-hm"),
        "ko": ("오~", "음~", "아~", "오오", "응응"),
        "ja": ("おお~", "うーん", "あ~", "うんうん"),
    }

    def __init__(self, language: str | None, rng: random.Random | None = None):
        self._words = self.WORDS.get((language or "en")[:2], self.WORDS["en"])
        self._rng = rng or random.Random()
        self._last: str | None = None

    @property
    def words(self) -> tuple[str, ...]:
        """All reactions for this language."""
        return self._words

    def next(self) -> str:
        """Return a reaction different from the previous one."""
        choices = [w for w in self._words if w != self._last]
        self._last = self._rng.choice(choices)
        return self._last


ReactionFetch = Callable[[str], Awaitable[bytes]]

# ElevenLabs PCM output rate used for prerendered reactions
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


async def replay(frames: list[rtc.AudioFrame]) -> AsyncIterator[rtc.AudioFrame]:
    """Yield cached frames as an audio stream for session.say()."""
    for frame in frames:
        yield frame
