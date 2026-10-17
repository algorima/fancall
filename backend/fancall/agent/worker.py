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
import re
from functools import partial

import httpx
from aioia_core.settings import FishAudioSettings, HedraSettings, OpenAIAPISettings
from livekit import agents
from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli
from livekit.agents.types import NOT_GIVEN, NotGiven
from livekit.plugins import fishaudio, hedra, openai
from PIL import Image
from pydantic import ValidationError

from fancall.agent.call_timer import run_call_timer
from fancall.persona import DEFAULT_PERSONA, Persona
from fancall.prompts import (
    OPENING_INSTRUCTIONS,
    PHONE_OPENING_MESSAGE,
    compose_instructions,
)
from fancall.schemas import AgentDispatchRequest
from fancall.settings import FancallCallSettings, FancallModelSettings, LiveKitSettings

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

    def __init__(
        self,
        instructions: str = DEFAULT_SYSTEM_PROMPT,
        opening_message: str | None = None,
        **kwargs,
    ):
        super().__init__(instructions=instructions, **kwargs)
        self.opening_message = opening_message

    async def on_enter(self) -> None:
        """Called when agent becomes active in the session."""
        # 고정 첫 멘트가 있으면 LLM 없이 그대로 읽는다
        if self.opening_message:
            self.session.say(self.opening_message, allow_interruptions=False)
            return
        # 실제 영통처럼 소리·화면 확인과 인사로 먼저 말을 건다
        self.session.generate_reply(instructions=OPENING_INSTRUCTIONS)


async def entrypoint(  # pylint: disable=too-many-locals
    ctx: JobContext,
    default_persona: Persona,
    livekit_settings: LiveKitSettings,  # pylint: disable=unused-argument
    openai_settings: OpenAIAPISettings,  # pylint: disable=unused-argument
    fish_settings: FishAudioSettings,
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
        fish_settings: Fish Audio TTS settings
        hedra_settings: Hedra avatar settings
        model_settings: Fancall LLM model settings
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
    avatar_id = metadata.avatar_id or default_persona.avatar_id
    profile_picture_url = (
        metadata.profile_picture_url or default_persona.profile_picture_url
    )
    voice_id = metadata.voice_id or default_persona.voice_id
    system_prompt = metadata.system_prompt or default_persona.system_prompt

    phone_call = metadata.phone_call

    logger.info(
        "Agent configuration: avatar_id=%s, voice_id=%s, phone_call=%s",
        avatar_id,
        voice_id,
        phone_call,
    )

    # Initialize components
    llm = openai.LLM(model=model_settings.openai_model)
    if voice_id:
        logger.info("Using Fish Audio voice_id: %s", voice_id)

    tts = fishaudio.TTS(
        api_key=fish_settings.api_key or NOT_GIVEN,
        reference_id=voice_id or NOT_GIVEN,
    )

    # 전화는 팬 목소리를 들어야 대화가 된다. 서버 VAD 스트리밍이라 별도 VAD가 필요 없다
    stt: openai.STT | NotGiven = (
        openai.STT(
            model=model_settings.stt_model,
            language=model_settings.stt_language,
            use_realtime=True,
        )
        if phone_call
        else NOT_GIVEN
    )

    session: AgentSession = AgentSession(llm=llm, tts=tts, stt=stt)

    # Initialize Hedra avatar if enabled
    avatar_session = None

    # 전화에는 화면이 없으므로 아바타를 띄우지 않는다
    if hedra_settings.enabled and not phone_call:
        hedra_api_key = hedra_settings.api_key
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
    instructions = compose_instructions(
        system_prompt,
        include_role_playing=False,
        include_video_call=True,
        include_phone_call=phone_call,
    )
    logger.info(
        "Using instructions: %s",
        instructions[:100] + "..." if len(instructions) > 100 else instructions,
    )

    opening_message = metadata.opening_message or (
        PHONE_OPENING_MESSAGE if phone_call else None
    )
    agent = CompanionAgent(instructions=instructions, opening_message=opening_message)
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
    fish_settings: FishAudioSettings,
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
        fish_settings: Fish Audio TTS settings
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
            fish_settings=fish_settings,
            hedra_settings=hedra_settings,
            model_settings=model_settings,
            call_settings=call_settings,
        ),
        worker_type=agents.WorkerType.ROOM,
        agent_name=livekit_settings.agent_name,
    )


def main() -> None:
    """Main function to run the agent worker."""
    livekit_settings = LiveKitSettings()
    openai_settings = OpenAIAPISettings()
    fish_settings = FishAudioSettings()
    hedra_settings = HedraSettings()
    model_settings = FancallModelSettings()
    call_settings = FancallCallSettings()
    cli.run_app(
        create_worker_options(
            DEFAULT_PERSONA,
            livekit_settings,
            openai_settings,
            fish_settings,
            hedra_settings,
            model_settings,
            call_settings,
        )
    )


if __name__ == "__main__":
    main()
