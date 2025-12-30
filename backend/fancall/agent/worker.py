#!/usr/bin/env python3
"""
LiveKit Agent Worker with Fish Audio TTS Integration

This file runs a real-time AI agent using Fish Audio TTS and, optionally,
a Hedra avatar.
"""

import asyncio
import base64
import io
import logging
import os
import re
from functools import partial

import httpx
from livekit import agents
from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli
from livekit.agents.types import NOT_GIVEN
from livekit.plugins import fishaudio, hedra, openai
from PIL import Image
from pydantic import ValidationError

from fancall.persona import DEFAULT_PERSONA, Persona
from fancall.prompts import compose_instructions
from fancall.schemas import AgentDispatchRequest
from fancall.settings import LiveKitSettings

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
        # Initial greeting could be generated here if needed


async def entrypoint(  # pylint: disable=too-many-locals
    ctx: JobContext,
    default_persona: Persona,
    settings: LiveKitSettings,  # pylint: disable=unused-argument
) -> None:
    """
    Agent entrypoint. Initializes AgentSession for text-to-speech tasks.

    Args:
        ctx: LiveKit job context
        default_persona: Default persona for fallback configuration
        settings: LiveKit settings with API credentials (reserved for future use)
    """
    logger.info("Agent entrypoint called for room: %s", ctx.room.name)

    # Check required environment variables before connecting
    required_env_vars = [
        "FISH_API_KEY",
        "OPENAI_API_KEY",
        "LIVEKIT_URL",
        "LIVEKIT_API_KEY",
        "LIVEKIT_API_SECRET",
    ]
    missing_vars = [v for v in required_env_vars if not os.getenv(v)]
    if missing_vars:
        logger.error(
            "Missing required environment variables: %s", ", ".join(missing_vars)
        )
        raise RuntimeError(f"Missing environment variables: {', '.join(missing_vars)}")

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
    profile_picture_url = (
        metadata.profile_picture_url or default_persona.profile_picture_url
    )
    voice_id = metadata.voice_id or default_persona.voice_id
    system_prompt = metadata.system_prompt or default_persona.system_prompt

    logger.info(
        "Agent configuration: avatar_id=%s, voice_id=%s",
        avatar_id,
        voice_id,
    )

    # Initialize components
    llm = openai.LLM(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    if voice_id:
        logger.info("Using Fish Audio voice_id: %s", voice_id)

    tts = fishaudio.TTS(
        api_key=os.getenv("FISH_API_KEY") or NOT_GIVEN,
        reference_id=voice_id or NOT_GIVEN,
    )

    session: AgentSession = AgentSession(llm=llm, tts=tts)

    # Initialize Hedra avatar if enabled
    hedra_enabled = os.getenv("HEDRA_ENABLED", "false").lower() == "true"
    avatar_session = None

    if hedra_enabled:
        # Get Hedra API key
        hedra_api_key = os.getenv("HEDRA_API_KEY")
        if not hedra_api_key:
            logger.error("HEDRA_API_KEY is required when HEDRA_ENABLED=true")
            ctx.shutdown(reason="HEDRA_API_KEY is required when HEDRA_ENABLED=true")
            return

        if avatar_id:
            logger.info("Hedra avatar is enabled with avatar_id: %s", avatar_id)
            avatar_session = hedra.AvatarSession(
                avatar_id=avatar_id,
                api_key=hedra_api_key,
            )
        elif profile_picture_url:
            # At this point, profile_picture_url is guaranteed to be str
            url = profile_picture_url
            logger.info(
                "Hedra avatar is enabled with profile_picture_url: %s",
                url[:100] + "..." if len(url) > 100 else url,
            )

            # Handle both data URLs and HTTP(S) URLs
            if url.startswith("data:"):
                # Extract base64 data from data URL
                match = re.match(r"data:image/[^;]+;base64,(.+)", url)
                if match:
                    base64_data = match.group(1)
                    image_bytes = base64.b64decode(base64_data)
                    avatar_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                else:
                    logger.error("Invalid data URL format")
                    ctx.shutdown(
                        reason="Invalid data URL format for profile_picture_url"
                    )
                    return
            else:
                # Regular HTTP(S) URL
                async with httpx.AsyncClient() as client:
                    response = await client.get(url)
                    response.raise_for_status()
                    avatar_image = Image.open(io.BytesIO(response.content)).convert(
                        "RGB"
                    )

            avatar_session = hedra.AvatarSession(
                avatar_image=avatar_image,
                api_key=hedra_api_key,
            )
        else:
            logger.error(
                "No avatar_id or profile_picture_url found. Cannot initialize Hedra avatar."
            )
            ctx.shutdown(
                reason="No avatar_id or profile_picture_url found for Hedra avatar"
            )
            return

        await avatar_session.start(agent_session=session, room=ctx.room)

    # Compose instructions from merged system prompt (Context Composer pattern)
    instructions = compose_instructions(system_prompt, include_role_playing=True)
    logger.info(
        "Using instructions: %s",
        instructions[:100] + "..." if len(instructions) > 100 else instructions,
    )

    agent = CompanionAgent(instructions=instructions)
    await session.start(agent=agent, room=ctx.room)
    logger.info("Agent session started.")

    # Free trial: auto-shutdown after 75 seconds
    try:
        await asyncio.sleep(75)
        logger.info("Free trial session limit (75s) reached. Shutting down.")
        ctx.shutdown(reason="Free trial session limit reached (75 seconds)")
    except asyncio.CancelledError:
        logger.info("Agent session cancelled before trial limit.")


def create_worker_options(
    default_persona: Persona, settings: LiveKitSettings
) -> WorkerOptions:
    """
    Create WorkerOptions for the agent with dependency injection.

    Uses functools.partial for pickle-safe DI (required by multiprocessing).

    Args:
        default_persona: Default persona for agent configuration
        settings: LiveKit settings with API credentials

    Returns:
        WorkerOptions configured with the agent entrypoint
    """
    return WorkerOptions(
        entrypoint_fnc=partial(
            entrypoint,
            default_persona=default_persona,
            settings=settings,
        ),
        worker_type=agents.WorkerType.ROOM,
        agent_name=settings.agent_name,
    )


def main() -> None:
    """Main function to run the agent worker."""
    settings = LiveKitSettings()
    cli.run_app(create_worker_options(DEFAULT_PERSONA, settings))


if __name__ == "__main__":
    main()
