"""
Turns the agent's speech audio into a synchronized stream of face frames.

Flow (LiveKit's `AvatarRunner` drives it):

    agent TTS audio ──push_audio()──▶ ┌────────────────────────┐
                                     │ RenderedVideoGenerator │──▶ video frame (40 ms)
    (nothing playing) ───────────────▶│  speaking: renderer    │──▶ audio frame (40 ms)
                                     │  listening: silence or │──▶ ... AudioSegmentEnd
                                     │             idle clip  │
                                     └────────────────────────┘

- Audio arrives at the TTS sample rate; it is resampled to 16 kHz for the
  renderer and to the output rate for the room, cut into 40 ms steps.
- Each 40 ms step yields one video frame and one audio frame, so audio and
  video stay in sync however slow or fast the renderer is.
- While no speech is queued, a continuous renderer is fed silence at real
  time (the face keeps listening); a plain renderer's frames are replaced by
  the idle clip.
- `clear_buffer` (the fan interrupted) drops queued speech and tells the
  renderer to forget it, so the mouth stops with the voice.
"""

import asyncio
import logging
import time
from collections.abc import AsyncIterator, Coroutine

import numpy as np
from livekit import rtc
from livekit.agents.voice.avatar import AudioSegmentEnd, VideoGenerator

from fancall.agent.avatar.idle_clip import IdleClip
from fancall.agent.avatar.renderer import (
    FPS,
    RENDER_SAMPLE_RATE,
    SAMPLES_PER_FRAME,
    Renderer,
)

logger = logging.getLogger(__name__)

FRAME_SECONDS = 1.0 / FPS
# Audio handed to the renderer per call: fewer calls than one per frame, but
# short enough that the mouth starts moving quickly after the voice starts.
RENDER_CHUNK_FRAMES = 5


class _Resampled:
    """Int16 PCM queue that resamples pushed frames to one rate."""

    def __init__(self, output_rate: int):
        self._rate = output_rate
        self._resampler: rtc.AudioResampler | None = None
        self._input_rate = 0
        self._buffer: np.ndarray = np.zeros(0, dtype=np.int16)

    def push(self, frame: rtc.AudioFrame) -> None:
        """Add a frame (mono or stereo, any rate)."""
        samples = np.frombuffer(frame.data, dtype=np.int16)
        if frame.num_channels > 1:
            samples = (
                samples.reshape(-1, frame.num_channels).mean(axis=1).astype(np.int16)
            )
        if frame.sample_rate != self._rate:
            if self._resampler is None or self._input_rate != frame.sample_rate:
                self._resampler = rtc.AudioResampler(frame.sample_rate, self._rate)
                self._input_rate = frame.sample_rate
            mono = rtc.AudioFrame(samples.tobytes(), frame.sample_rate, 1, len(samples))
            samples = np.concatenate(
                [
                    np.frombuffer(out.data, dtype=np.int16)
                    for out in self._resampler.push(mono)
                ]
            )
        self._buffer = np.concatenate([self._buffer, samples])

    def flush(self) -> None:
        """Push out what the resampler still holds."""
        if self._resampler is not None:
            for out in self._resampler.flush():
                self._buffer = np.concatenate(
                    [self._buffer, np.frombuffer(out.data, dtype=np.int16)]
                )

    def available(self) -> int:
        """Samples queued."""
        return len(self._buffer)

    def take(self, count: int, *, pad: bool = False) -> np.ndarray | None:
        """Remove and return `count` samples; None when fewer are buffered (unless `pad`)."""
        if len(self._buffer) < count:
            if not pad or len(self._buffer) == 0:
                return None
            self._buffer = np.concatenate(
                [self._buffer, np.zeros(count - len(self._buffer), dtype=np.int16)]
            )
        out, self._buffer = self._buffer[:count], self._buffer[count:]
        return out

    def clear(self) -> None:
        """Drop everything queued."""
        self._buffer = np.zeros(0, dtype=np.int16)
        self._resampler = None


class RenderedVideoGenerator(VideoGenerator):
    """Video (and the matching audio) of the trainee speaking and listening."""

    def __init__(
        self,
        renderer: Renderer,
        *,
        idle: IdleClip | None = None,
        output_sample_rate: int = 24_000,
        render_chunk_frames: int = RENDER_CHUNK_FRAMES,
    ):
        if not renderer.continuous and idle is None:
            raise ValueError("a renderer that is not continuous needs an idle clip")
        self._renderer = renderer
        self._idle = idle
        self._out_rate = output_sample_rate
        self._chunk_frames = render_chunk_frames
        self._render_audio = _Resampled(RENDER_SAMPLE_RATE)
        self._play_audio = _Resampled(output_sample_rate)
        self._segment_end_pending = False
        self._generation = 0  # bumped by clear_buffer to drop in-flight frames
        self._wakeup = asyncio.Event()
        self._closed = False
        self._idle_index = 0

    async def start(self) -> None:
        """Start the renderer."""
        await self._renderer.start()

    async def push_audio(self, frame: rtc.AudioFrame | AudioSegmentEnd) -> None:
        if isinstance(frame, AudioSegmentEnd):
            self._render_audio.flush()
            self._play_audio.flush()
            self._segment_end_pending = True
        else:
            self._render_audio.push(frame)
            self._play_audio.push(frame)
        self._wakeup.set()

    def clear_buffer(self) -> Coroutine[None, None, None]:
        return self._clear()

    async def _clear(self) -> None:
        self._generation += 1
        self._render_audio.clear()
        self._play_audio.clear()
        self._segment_end_pending = False
        await self._renderer.reset()
        self._wakeup.set()

    async def aclose(self) -> None:
        """Stop the stream and the renderer."""
        self._closed = True
        self._wakeup.set()
        await self._renderer.aclose()

    def __aiter__(
        self,
    ) -> AsyncIterator[rtc.VideoFrame | rtc.AudioFrame | AudioSegmentEnd]:
        return self._stream()

    async def _stream(
        self,
    ) -> AsyncIterator[rtc.VideoFrame | rtc.AudioFrame | AudioSegmentEnd]:
        next_tick = time.monotonic()
        while not self._closed:
            generation = self._generation
            speech = self._take_speech()
            if speech is not None:
                async for item in self._speak(speech, generation):
                    yield item
                next_tick = time.monotonic()
                continue

            if self._segment_end_pending:
                # A renderer that draws with lookahead still owes frames for
                # the last audio: push silence until that audio has played
                owed = 0
                while (
                    self._play_audio.available() > 0 and generation == self._generation
                ):
                    before = self._play_audio.available()
                    silence = np.zeros(SAMPLES_PER_FRAME, dtype=np.int16)
                    async for item in self._speak(silence, generation):
                        yield item
                    owed = owed + 1 if self._play_audio.available() == before else 0
                    if owed > self._chunk_frames * 2:
                        logger.warning(
                            "renderer did not return the frames it owes; dropping audio"
                        )
                        self._play_audio.clear()
                self._segment_end_pending = False
                yield AudioSegmentEnd()
                continue

            # Nothing to say: keep the face alive in real time
            frame = await self._listen_frame(generation)
            next_tick += FRAME_SECONDS
            delay = next_tick - time.monotonic()
            if delay > 0:
                try:
                    await asyncio.wait_for(self._wakeup.wait(), timeout=delay)
                except asyncio.TimeoutError:
                    pass
            self._wakeup.clear()
            if frame is not None and generation == self._generation:
                yield frame

    def _take_speech(self) -> np.ndarray | None:
        """The next chunk of speech to render, or None when there is none."""
        chunk = SAMPLES_PER_FRAME * self._chunk_frames
        available = self._render_audio.available()
        if available >= chunk:
            return self._render_audio.take(chunk)
        if self._segment_end_pending and available > 0:
            # The tail of the reply: whole frames, the last one padded with silence
            frames = -(-available // SAMPLES_PER_FRAME)
            return self._render_audio.take(frames * SAMPLES_PER_FRAME, pad=True)
        return None

    async def _speak(
        self, speech: np.ndarray, generation: int
    ) -> AsyncIterator[rtc.VideoFrame | rtc.AudioFrame]:
        """Render a chunk and pair each returned frame with the next 40 ms of audio.

        A renderer with lookahead may return fewer frames than the chunk holds;
        the unpaired audio waits for the next call.
        """
        frames = await self._renderer.render(speech)
        if generation != self._generation:
            return  # interrupted while rendering
        play_step = int(self._out_rate * FRAME_SECONDS)
        for image in frames:
            audio = self._play_audio.take(play_step, pad=True)
            if audio is None:
                audio = np.zeros(play_step, dtype=np.int16)
            yield _video_frame(image)
            yield rtc.AudioFrame(audio.tobytes(), self._out_rate, 1, play_step)

    async def _listen_frame(self, generation: int) -> rtc.VideoFrame | None:
        if self._renderer.continuous:
            frames = await self._renderer.render(
                np.zeros(SAMPLES_PER_FRAME, dtype=np.int16)
            )
            if generation != self._generation or not frames:
                return None
            return _video_frame(frames[-1])
        assert self._idle is not None
        image = self._idle.frame(self._idle_index)
        self._idle_index += 1
        return _video_frame(image)


def _video_frame(image: np.ndarray) -> rtc.VideoFrame:
    height, width = image.shape[:2]
    return rtc.VideoFrame(
        width, height, rtc.VideoBufferType.RGBA, np.ascontiguousarray(image).tobytes()
    )
