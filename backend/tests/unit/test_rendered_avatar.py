"""
Unit tests for the self-rendered avatar: audio in, synchronized frames out
"""

import asyncio
import unittest

import numpy as np
from livekit import rtc
from livekit.agents.voice.avatar import AudioSegmentEnd

from fancall.agent.avatar import FakeRenderer, IdleClip, RenderedVideoGenerator
from fancall.agent.avatar.renderer import SAMPLES_PER_FRAME, Renderer

WIDTH, HEIGHT = 32, 48


def _blank() -> np.ndarray:
    return np.zeros((HEIGHT, WIDTH, 4), dtype=np.uint8)


def _tone(seconds: float, rate: int = 24_000) -> rtc.AudioFrame:
    count = int(rate * seconds)
    t = np.arange(count) / rate
    samples = (np.sin(2 * np.pi * 220 * t) * 12000).astype(np.int16)
    return rtc.AudioFrame(samples.tobytes(), rate, 1, count)


async def _collect(
    generator: RenderedVideoGenerator, count: int, timeout: float = 2.0
) -> list:
    items: list = []
    stream = aiter(generator)

    async def _run() -> None:
        async for item in stream:
            items.append(item)
            if len(items) >= count:
                return

    await asyncio.wait_for(_run(), timeout)
    return items


class IdleClipTest(unittest.TestCase):
    def test_loops_back_and_forth_without_a_seam(self):
        frames = [np.full((2, 2, 4), i, dtype=np.uint8) for i in range(4)]
        clip = IdleClip(frames, fps=25)
        order = [int(clip.frame(i)[0, 0, 0]) for i in range(8)]
        self.assertEqual(order, [0, 1, 2, 3, 2, 1, 0, 1])

    def test_single_frame_clip(self):
        clip = IdleClip.still(_blank())
        self.assertEqual(clip.size, (WIDTH, HEIGHT))
        self.assertIs(clip.frame(7), clip.frame(0))


class FakeRendererTest(unittest.TestCase):
    def test_one_frame_per_40ms_and_mouth_opens_with_sound(self):
        renderer = FakeRenderer(_blank())
        silence = np.zeros(SAMPLES_PER_FRAME * 3, dtype=np.int16)
        loud = (np.sin(np.arange(SAMPLES_PER_FRAME * 2) / 5) * 20000).astype(np.int16)
        quiet = asyncio.run(renderer.render(silence))
        spoken = asyncio.run(renderer.render(loud))
        self.assertEqual((len(quiet), len(spoken)), (3, 2))
        self.assertGreater(int(spoken[0][..., 0].sum()), int(quiet[0][..., 0].sum()))


class RenderedVideoGeneratorTest(unittest.TestCase):
    def test_speech_gives_one_video_and_one_audio_frame_per_40ms(self):
        async def run():
            generator = RenderedVideoGenerator(
                FakeRenderer(_blank()),
                idle=IdleClip.still(_blank()),
                output_sample_rate=24_000,
            )
            await generator.push_audio(_tone(0.4))  # 10 frames
            await generator.push_audio(AudioSegmentEnd())
            return await _collect(generator, 21)

        items = asyncio.run(run())
        videos = [i for i in items if isinstance(i, rtc.VideoFrame)]
        audios = [i for i in items if isinstance(i, rtc.AudioFrame)]
        self.assertEqual((len(videos), len(audios)), (10, 10))
        self.assertIsInstance(items[-1], AudioSegmentEnd)
        # Audio comes out at the room rate in 40 ms steps, right after its frame
        self.assertEqual(audios[0].sample_rate, 24_000)
        self.assertEqual(audios[0].samples_per_channel, 960)
        self.assertIsInstance(items[0], rtc.VideoFrame)
        self.assertIsInstance(items[1], rtc.AudioFrame)

    def test_partial_last_frame_is_padded_not_dropped(self):
        async def run():
            generator = RenderedVideoGenerator(
                FakeRenderer(_blank()),
                idle=IdleClip.still(_blank()),
                output_sample_rate=16_000,
            )
            await generator.push_audio(_tone(0.05, rate=16_000))  # 1.25 frames
            await generator.push_audio(AudioSegmentEnd())
            return await _collect(generator, 5)

        items = asyncio.run(run())
        self.assertEqual(len([i for i in items if isinstance(i, rtc.VideoFrame)]), 2)
        self.assertIsInstance(items[-1], AudioSegmentEnd)

    def test_idle_frames_keep_coming_while_nobody_speaks(self):
        async def run():
            generator = RenderedVideoGenerator(
                FakeRenderer(_blank()),
                idle=IdleClip.still(_blank()),
                output_sample_rate=16_000,
            )
            return await _collect(generator, 3)

        items = asyncio.run(run())
        self.assertTrue(all(isinstance(i, rtc.VideoFrame) for i in items))

    def test_clear_buffer_drops_queued_speech(self):
        async def run():
            renderer = FakeRenderer(_blank())
            generator = RenderedVideoGenerator(
                renderer, idle=IdleClip.still(_blank()), output_sample_rate=16_000
            )
            await generator.push_audio(_tone(2.0, rate=16_000))
            await generator.clear_buffer()
            items = await _collect(generator, 3)
            return renderer.rendered_frames, items

        rendered, items = asyncio.run(run())
        self.assertEqual(rendered, 0)
        self.assertTrue(all(isinstance(i, rtc.VideoFrame) for i in items))

    def test_continuous_renderer_is_fed_silence_while_listening(self):
        class Continuous(Renderer):
            continuous = True

            def __init__(self):
                self.calls: list[int] = []

            async def render(self, pcm):
                self.calls.append(int(np.abs(pcm).max()))
                return [_blank() for _ in range(len(pcm) // SAMPLES_PER_FRAME)]

        async def run():
            renderer = Continuous()
            generator = RenderedVideoGenerator(renderer, output_sample_rate=16_000)
            await _collect(generator, 2)
            return renderer.calls

        calls = asyncio.run(run())
        self.assertGreaterEqual(len(calls), 2)
        self.assertEqual(set(calls), {0})

    def test_needs_an_idle_clip_without_a_continuous_renderer(self):
        with self.assertRaises(ValueError):
            RenderedVideoGenerator(FakeRenderer(_blank()))


if __name__ == "__main__":
    unittest.main()
