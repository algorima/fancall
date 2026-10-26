"""
Wires the self-rendered avatar into a LiveKit agent session.

The agent's audio output is replaced by a queue; LiveKit's `AvatarRunner`
reads it, feeds `RenderedVideoGenerator`, and publishes the video and audio
tracks on the agent's own participant (the frontend already shows any video
track an agent publishes).
"""

import logging

from livekit import rtc
from livekit.agents import AgentSession
from livekit.agents.voice.avatar import AvatarOptions, AvatarRunner, QueueAudioOutput

from fancall.agent.avatar.renderer import FPS
from fancall.agent.avatar.video_generator import RenderedVideoGenerator

logger = logging.getLogger(__name__)


async def start_rendered_avatar(
    session: AgentSession,
    room: rtc.Room,
    generator: RenderedVideoGenerator,
    *,
    size: tuple[int, int],
    output_sample_rate: int,
) -> AvatarRunner:
    """Route the agent's speech through the generator and publish its frames."""
    audio_output = QueueAudioOutput(sample_rate=output_sample_rate)
    session.output.audio = audio_output
    await generator.start()
    width, height = size
    runner = AvatarRunner(
        room,
        audio_recv=audio_output,
        video_gen=generator,
        options=AvatarOptions(
            video_width=width,
            video_height=height,
            video_fps=FPS,
            audio_sample_rate=output_sample_rate,
            audio_channels=1,
        ),
    )
    await runner.start()
    logger.info("Rendered avatar started: %dx%d at %d fps", width, height, FPS)
    return runner
