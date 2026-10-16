#!/usr/bin/env python3
"""
LiveKit Agent Worker with ElevenLabs TTS Integration

This file runs a real-time AI agent using ElevenLabs TTS.
"""

import asyncio
import logging
from functools import partial

from aioia_core.settings import HedraSettings, OpenAIAPISettings
from livekit import agents
from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli
from livekit.agents.types import NOT_GIVEN
from livekit.plugins import elevenlabs, openai
from pydantic import ValidationError

from fancall.agent.call_timer import run_call_timer
from fancall.persona import DEFAULT_PERSONA, Persona
from fancall.prompts import OPENING_INSTRUCTIONS, compose_instructions
from fancall.schemas import AgentDispatchRequest
from fancall.settings import (
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


async def entrypoint(
    ctx: JobContext,
    default_persona: Persona,
    livekit_settings: LiveKitSettings,  # pylint: disable=unused-argument
    openai_settings: OpenAIAPISettings,  # pylint: disable=unused-argument
    elevenlabs_settings: ElevenLabsSettings,
    hedra_settings: HedraSettings,
    model_settings: FancallModelSettings,
    call_settings: FancallCallSettings,
) -> None:
    """
    Agent entrypoint. Initializes AgentSession for text-to-speech tasks.

    Args:
        ctx: LiveKit job context
        default_persona: Default persona for fallback configuration
        livekit_settings: LiveKit settings with API credentials (reserved for future use)
        openai_settings: OpenAI API settings (현재 미사용: livekit.plugins.openai가 환경변수 직접 사용)
        elevenlabs_settings: ElevenLabs TTS settings
        hedra_settings: Hedra avatar settings (discontinued; only used to warn)
        model_settings: Fancall LLM/TTS model settings
        call_settings: Video call timing settings
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
    voice_id = metadata.voice_id or default_persona.voice_id
    system_prompt = metadata.system_prompt or default_persona.system_prompt

    logger.info(
        "Agent configuration: voice_id=%s, elevenlabs_model=%s",
        voice_id,
        model_settings.elevenlabs_model,
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

    # Hedra sunset its realtime avatar service; livekit-plugins-hedra no longer works.
    # The frontend falls back to the profile picture when no agent video track exists.
    if hedra_settings.enabled:
        logger.warning(
            "HEDRA_ENABLED=true is ignored: Hedra realtime avatar has been discontinued."
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
    try:
        await run_call_timer(session, agent, instructions, call_settings)
        logger.info(
            "Call limit (%.0fs) reached. Shutting down.",
            call_settings.call_duration_seconds,
        )
        ctx.shutdown(reason="Call time limit reached")
    except asyncio.CancelledError:
        logger.info("Agent session cancelled before call limit.")


def create_worker_options(
    default_persona: Persona,
    livekit_settings: LiveKitSettings,
    openai_settings: OpenAIAPISettings,
    elevenlabs_settings: ElevenLabsSettings,
    hedra_settings: HedraSettings,
    model_settings: FancallModelSettings,
    call_settings: FancallCallSettings,
) -> WorkerOptions:
    """
    Create WorkerOptions for the agent with dependency injection.

    Uses functools.partial for pickle-safe DI (required by multiprocessing).

    Args:
        default_persona: Default persona for agent configuration
        livekit_settings: LiveKit settings with API credentials
        openai_settings: OpenAI API settings
        elevenlabs_settings: ElevenLabs TTS settings
        hedra_settings: Hedra avatar settings
        model_settings: Fancall LLM model settings
        call_settings: Video call timing settings

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
            hedra_settings=hedra_settings,
            model_settings=model_settings,
            call_settings=call_settings,
        ),
        worker_type=agents.WorkerType.ROOM,
        agent_name=livekit_settings.agent_name,
        ws_url=livekit_settings.url,
        api_key=livekit_settings.api_key,
        api_secret=livekit_settings.api_secret,
    )


def main() -> None:
    """Main function to run the agent worker."""
    livekit_settings = LiveKitSettings()
    openai_settings = OpenAIAPISettings()
    elevenlabs_settings = ElevenLabsSettings()
    hedra_settings = HedraSettings()
    model_settings = FancallModelSettings()
    call_settings = FancallCallSettings()
    cli.run_app(
        create_worker_options(
            DEFAULT_PERSONA,
            livekit_settings,
            openai_settings,
            elevenlabs_settings,
            hedra_settings,
            model_settings,
            call_settings,
        )
    )


if __name__ == "__main__":
    main()
