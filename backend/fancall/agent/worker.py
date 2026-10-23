#!/usr/bin/env python3
"""
LiveKit Agent Worker with ElevenLabs TTS Integration

This file runs a real-time AI agent using ElevenLabs TTS and, when configured,
a lip-synced avatar (Anam, Tavus, Simli or LemonSlice).
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from functools import partial
from typing import Any

from aioia_core.settings import HedraSettings, OpenAIAPISettings
from livekit import agents
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    ModelSettings,
    WorkerOptions,
    cli,
    inference,
)
from livekit.agents.llm import ChatContext, ChatMessage, Tool
from livekit.agents.types import NOT_GIVEN
from livekit.plugins import anam, elevenlabs, lemonslice, openai, simli, tavus
from pydantic import ValidationError

from fancall.agent.call_timer import run_call_timer
from fancall.agent.hangup import end_call_when_fan_leaves
from fancall.agent.latency_log import log_latency
from fancall.agent.quiet_nudge import QuietNudger
from fancall.agent.reply_limit import limit_sentences
from fancall.persona import DEFAULT_PERSONA, Persona
from fancall.prompts import (
    OPENING_INSTRUCTIONS,
    compose_instructions,
    opening_user_input,
)
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
# Real idols speak about 1.3 seconds at a time; anything longer is cut
MAX_REPLY_SENTENCES = 2


class CompanionAgent(Agent):
    """
    A voice-enabled AI companion agent.
    Processes user input and generates conversational responses using LLM and TTS.
    """

    def __init__(
        self,
        instructions: str = DEFAULT_SYSTEM_PROMPT,
        language: str | None = None,
        **kwargs,
    ):
        super().__init__(instructions=instructions, **kwargs)
        self._language = language

    async def on_enter(self) -> None:
        """Called when agent becomes active in the session."""
        # 실제 영통처럼 소리·화면 확인과 인사로 먼저 말을 건다
        self.session.generate_reply(
            user_input=opening_user_input(self._language),
            instructions=OPENING_INSTRUCTIONS,
        )

    def llm_node(
        self,
        chat_ctx: ChatContext,
        tools: list[Tool],
        model_settings: ModelSettings,
    ) -> AsyncIterator[Any]:
        """Generate the reply, cut to MAX_REPLY_SENTENCES before it is spoken."""
        reply = Agent.default.llm_node(self, chat_ctx, tools, model_settings)
        return limit_sentences(reply, MAX_REPLY_SENTENCES)


# The frontend stops ringing after 25 seconds; give the fan's join a margin.
ANSWER_TIMEOUT_SECONDS = 60


async def wait_for_answer(ctx: JobContext, timeout: float) -> bool:
    """
    Wait for the fan to join the room before starting paid media.

    The frontend dispatches the agent while the phone is still ringing so the
    worker is ready when the fan answers. The avatar (billed per minute) and
    the session timer start only after the fan joins. An unanswered call ends
    the job here.
    """
    try:
        await asyncio.wait_for(ctx.wait_for_participant(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.info("Call was not answered within %ss. Shutting down.", timeout)
        ctx.shutdown(reason="Call was not answered")
        return False
    return True


async def start_avatar(
    ctx: JobContext,
    session: AgentSession,
    avatar_id: str | None,
    profile_picture_url: str | None,
    livekit_settings: LiveKitSettings,
    avatar_settings: AvatarSettings,
) -> None:
    """
    Start a lip-synced avatar that joins the room and speaks the agent's audio.

    Anam is preferred when configured, then Tavus; Simli is used for a pre-registered face
    (avatar_id); LemonSlice animates a profile picture URL directly. If no
    provider is configured or startup fails, the call continues voice-only and
    the frontend shows the profile picture.
    """
    avatar: (
        anam.AvatarSession
        | tavus.AvatarSession
        | simli.AvatarSession
        | lemonslice.AvatarSession
    )
    if avatar_settings.anam_api_key and avatar_settings.anam_avatar_id:
        logger.info(
            "Starting Anam avatar with avatar_id: %s", avatar_settings.anam_avatar_id
        )
        avatar = anam.AvatarSession(
            persona_config=anam.PersonaConfig(
                name="fancall", avatarId=avatar_settings.anam_avatar_id
            ),
            session_options=anam.SessionOptions(
                video_width=avatar_settings.anam_video_width,
                video_height=avatar_settings.anam_video_height,
            ),
            api_key=avatar_settings.anam_api_key,
        )
    elif avatar_settings.tavus_api_key:
        logger.info(
            "Starting Tavus avatar with face_id: %s",
            avatar_settings.tavus_face_id or "stock",
        )
        avatar = tavus.AvatarSession(
            api_key=avatar_settings.tavus_api_key,
            face_id=avatar_settings.tavus_face_id or NOT_GIVEN,
            pal_id=avatar_settings.tavus_pal_id or NOT_GIVEN,
        )
    elif avatar_id and avatar_settings.simli_api_key:
        logger.info("Starting Simli avatar with face_id: %s", avatar_id)
        avatar = simli.AvatarSession(
            simli_config=simli.SimliConfig(
                api_key=avatar_settings.simli_api_key,
                face_id=avatar_id,
            ),
        )
    elif (
        profile_picture_url
        and profile_picture_url.startswith("http")
        and avatar_settings.lemonslice_api_key
    ):
        logger.info("Starting LemonSlice avatar from profile picture")
        avatar = lemonslice.AvatarSession(
            agent_image_url=profile_picture_url,
            api_key=avatar_settings.lemonslice_api_key,
        )
    else:
        logger.info("No avatar provider configured for this persona; voice-only.")
        return

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
    hedra_settings: HedraSettings,
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
        hedra_settings: Hedra avatar settings (discontinued; only used to warn)
        model_settings: Fancall LLM/TTS model settings
        call_settings: Video call timing settings
        avatar_settings: Lip-synced avatar settings (read from env if omitted)
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
    avatar_id = metadata.avatar_id or default_persona.avatar_id
    profile_picture_url = (
        metadata.profile_picture_url or default_persona.profile_picture_url
    )
    system_prompt = metadata.system_prompt or default_persona.system_prompt

    logger.info(
        "Agent configuration: voice_id=%s, elevenlabs_model=%s",
        voice_id,
        model_settings.elevenlabs_model,
    )

    # Initialize components
    llm = openai.LLM(
        model=model_settings.openai_model,
        reasoning_effort=model_settings.openai_reasoning_effort or NOT_GIVEN,
    )
    if voice_id:
        logger.info("Using ElevenLabs voice_id: %s", voice_id)

    tts = elevenlabs.TTS(
        api_key=elevenlabs_settings.api_key or NOT_GIVEN,
        model=model_settings.elevenlabs_model,
        voice_id=voice_id or elevenlabs.DEFAULT_VOICE_ID,
    )

    # 팬이 말로 대화한다. Flux가 말 끝을 판단하고, 답은 그 전에 미리 만들어 둔다
    # (실제 영통팬싸 말 사이 쉼 중앙값 1.4초: docs/call-naturalness-criteria.md)
    session: AgentSession = AgentSession(
        llm=llm,
        tts=tts,
        stt=inference.STT(
            model_settings.stt_model,
            extra_kwargs=(
                {"eager_eot_threshold": model_settings.stt_eager_eot_threshold}
                if "flux" in model_settings.stt_model
                else NOT_GIVEN
            ),
        ),
        turn_handling={
            "turn_detection": "stt",
            "preemptive_generation": {"preemptive_tts": True},
        },
    )

    # Hedra sunset its realtime avatar service; livekit-plugins-hedra no longer works.
    if hedra_settings.enabled:
        logger.warning(
            "HEDRA_ENABLED=true is ignored: Hedra realtime avatar has been discontinued."
        )

    if not await wait_for_answer(ctx, ANSWER_TIMEOUT_SECONDS):
        return
    # 팬이 끊으면 아바타까지 바로 내보낸다 (Simli 세션·시간이 남지 않게)
    end_call_when_fan_leaves(ctx)

    await start_avatar(
        ctx,
        session,
        avatar_id,
        profile_picture_url,
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

    agent = CompanionAgent(instructions=instructions, language=metadata.language)

    # 팬이 조용하면 먼저 한마디 한다. 마무리 단계부터는 작별 인사와 겹치지 않게 멈춘다.
    nudger = QuietNudger(
        session,
        quiet_seconds=call_settings.quiet_nudge_seconds,
        max_in_row=call_settings.quiet_nudge_max_in_row,
    )
    session.on("agent_state_changed", lambda ev: nudger.on_agent_state(ev.new_state))
    session.on("user_state_changed", lambda ev: nudger.on_user_state(ev.new_state))
    log_latency(session)
    session.on(
        "conversation_item_added",
        lambda ev: (
            nudger.on_user_message(ev.item.text_content or "")
            if isinstance(ev.item, ChatMessage) and ev.item.role == "user"
            else None
        ),
    )
    asyncio.get_running_loop().call_later(
        call_settings.call_duration_seconds - call_settings.wrap_up_lead_seconds,
        nudger.stop,
    )

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
        hedra_settings: Hedra avatar settings
        model_settings: Fancall LLM model settings
        call_settings: Video call timing settings
        avatar_settings: Lip-synced avatar settings (read from env if omitted)

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
            avatar_settings=avatar_settings,
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
