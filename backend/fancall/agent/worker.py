#!/usr/bin/env python3
"""
LiveKit Agent Worker with ElevenLabs TTS Integration

This file runs a real-time AI agent using ElevenLabs TTS and, optionally,
a Simli lip-synced avatar.
"""

import asyncio
import logging
from functools import partial

from aioia_core.settings import OpenAIAPISettings
from livekit import agents
from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli
from livekit.agents.types import NOT_GIVEN
from livekit.plugins import elevenlabs, openai, simli
from pydantic import ValidationError

from fancall.agent.call_timer import run_call_timer
from fancall.persona import DEFAULT_PERSONA, Persona
from fancall.prompts import OPENING_INSTRUCTIONS, compose_instructions
from fancall.schemas import AgentDispatchRequest
from fancall.settings import (
    AvatarSettings,
    ElevenLabsSettings,
    FancallCallSettings,
    FancallModelSettings,
    LiveKitSettings,
)

# Basic logging configuration
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_SYSTEM_PROMPT = "You are a friendly and helpful AI companion."


class CompanionAgent(Agent):
    """
    A voice-enabled AI companion agent.
    Processes user input and generates conversational responses using LLM and TTS.
    """

    def __init__(self, instructions: str = DEFAULT_SYSTEM_PROMPT, **kwargs):
        super().__init__(instructions=instructions, **kwargs)

    async def on_enter(self) -> None:
        """Called when agent becomes active in the session."""
        # 실제 영통처럼 소리·화면 확인과 인사로 먼저 말을 건다
        self.session.generate_reply(instructions=OPENING_INSTRUCTIONS)


async def start_avatar(
    ctx: JobContext,
    session: AgentSession,
    avatar_id: str | None,
    livekit_settings: LiveKitSettings,
    avatar_settings: AvatarSettings,
) -> None:
    """
    Start a Simli lip-synced avatar that joins the room and speaks the agent's audio.

    Simli needs a pre-registered face (avatar_id) and an API key. Without them, or
    if startup fails, the call continues voice-only and the frontend shows the
    profile picture.
    """
    if not (avatar_id and avatar_settings.simli_api_key):
        logger.info("No Simli avatar configured for this persona; voice-only.")
        return

    logger.info("Starting Simli avatar with face_id: %s", avatar_id)
    avatar = simli.AvatarSession(
        simli_config=simli.SimliConfig(
            api_key=avatar_settings.simli_api_key,
            face_id=avatar_id,
        ),
    )
    try:
        await avatar.start(
            session,
            room=ctx.room,
            livekit_url=livekit_settings.url,
            livekit_api_key=livekit_settings.api_key,
            livekit_api_secret=livekit_settings.api_secret,
        )
    except Exception:  # pylint: disable=broad-exception-caught
        logger.exception("Avatar failed to start; continuing voice-only.")


async def entrypoint(
    ctx: JobContext,
    default_persona: Persona,
    livekit_settings: LiveKitSettings,
    openai_settings: OpenAIAPISettings,  # pylint: disable=unused-argument
    elevenlabs_settings: ElevenLabsSettings,
    model_settings: FancallModelSettings,
    call_settings: FancallCallSettings,
    avatar_settings: AvatarSettings | None = None,
) -> None:
    """
    Agent entrypoint. Initializes AgentSession for text-to-speech tasks.

    Args:
        ctx: LiveKit job context
        default_persona: Default persona for fallback configuration
        livekit_settings: LiveKit settings; the avatar joins the room with these
        openai_settings: OpenAI API settings (현재 미사용: livekit.plugins.openai가 환경변수 직접 사용)
        elevenlabs_settings: ElevenLabs TTS settings
        model_settings: Fancall LLM/TTS model settings
        call_settings: Video call timing settings
        avatar_settings: Simli avatar settings (read from env if omitted)
    """
    logger.info("Agent entrypoint called for room: %s", ctx.room.name)

    await ctx.connect()
    logger.info("Connected to LiveKit room: %s", ctx.room.name)

    # Parse job metadata to get dynamic configuration
    metadata = AgentDispatchRequest()
    if ctx.job.metadata:
        try:
            metadata = AgentDispatchRequest.model_validate_json(ctx.job.metadata)
        except ValidationError as e:
            logger.error("Failed to parse job metadata: %s", e)
            ctx.shutdown(reason="Invalid job metadata format")
            return

    # Merge metadata with default_persona (metadata takes precedence)
    avatar_id = metadata.avatar_id or default_persona.avatar_id
    voice_id = metadata.voice_id or default_persona.voice_id
    system_prompt = metadata.system_prompt or default_persona.system_prompt

    logger.info(
        "Agent configuration: avatar_id=%s, voice_id=%s",
        avatar_id,
        voice_id,
    )

    # Initialize components
    llm = openai.LLM(model=model_settings.openai_model)
    if voice_id:
        logger.info("Using ElevenLabs voice_id: %s", voice_id)

    tts = elevenlabs.TTS(
        api_key=elevenlabs_settings.api_key or NOT_GIVEN,
        model=model_settings.elevenlabs_model,
        voice_id=voice_id or elevenlabs.DEFAULT_VOICE_ID,
    )

    session: AgentSession = AgentSession(llm=llm, tts=tts)

    await start_avatar(
        ctx,
        session,
        avatar_id,
        livekit_settings,
        avatar_settings or AvatarSettings(),
    )

    # Compose instructions from merged system prompt (Context Composer pattern)
    instructions = compose_instructions(
        system_prompt, include_role_playing=False, include_video_call=True
    )
    logger.info(
        "Using instructions: %s",
        instructions[:100] + "..." if len(instructions) > 100 else instructions,
    )

    agent = CompanionAgent(instructions=instructions)
    await session.start(agent=agent, room=ctx.room)
    logger.info("Agent session started.")

    # Call limit: wrap up, say goodbye, then shut down
    timer = asyncio.create_task(
        run_call_timer(session, agent, instructions, call_settings)
    )
    # 팬이 먼저 끊으면 세션이 닫힌다. 타이머가 남아 있으면 작업이 끝나지 않고 강제 종료된다
    session.on("close", lambda _event: timer.cancel())
    try:
        await timer
        logger.info(
            "Call limit (%.0fs) reached. Shutting down.",
            call_settings.call_duration_seconds,
        )
        ctx.shutdown(reason="Call time limit reached")
    except asyncio.CancelledError:
        logger.info("Agent session ended before call limit.")


def create_worker_options(
    default_persona: Persona,
    livekit_settings: LiveKitSettings,
    openai_settings: OpenAIAPISettings,
    elevenlabs_settings: ElevenLabsSettings,
    model_settings: FancallModelSettings,
    call_settings: FancallCallSettings,
    avatar_settings: AvatarSettings | None = None,
) -> WorkerOptions:
    """
    Create WorkerOptions for the agent with dependency injection.

    Uses functools.partial for pickle-safe DI (required by multiprocessing).

    Args:
        default_persona: Default persona for agent configuration
        livekit_settings: LiveKit settings with API credentials
        openai_settings: OpenAI API settings
        elevenlabs_settings: ElevenLabs TTS settings
        model_settings: Fancall LLM/TTS model settings
        call_settings: Video call timing settings
        avatar_settings: Simli avatar settings (read from env if omitted)

    Returns:
        WorkerOptions configured with the agent entrypoint
    """
    return WorkerOptions(
        entrypoint_fnc=partial(
            entrypoint,
            default_persona=default_persona,
            livekit_settings=livekit_settings,
            openai_settings=openai_settings,
            elevenlabs_settings=elevenlabs_settings,
            model_settings=model_settings,
            call_settings=call_settings,
            avatar_settings=avatar_settings,
        ),
        worker_type=agents.WorkerType.ROOM,
        agent_name=livekit_settings.agent_name,
    )


def main() -> None:
    """Main function to run the agent worker."""
    livekit_settings = LiveKitSettings()
    openai_settings = OpenAIAPISettings()
    elevenlabs_settings = ElevenLabsSettings()
    model_settings = FancallModelSettings()
    call_settings = FancallCallSettings()
    cli.run_app(
        create_worker_options(
            DEFAULT_PERSONA,
            livekit_settings,
            openai_settings,
            elevenlabs_settings,
            model_settings,
            call_settings,
        )
    )


if __name__ == "__main__":
    main()
