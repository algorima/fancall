#!/usr/bin/env python3
"""
LiveKit Agent Worker with ElevenLabs TTS Integration

This file runs a real-time AI agent using ElevenLabs TTS and, optionally,
a Simli lip-synced avatar.
"""

import asyncio
import logging
import math
from collections.abc import AsyncIterator
from functools import partial
from typing import Any

import aiohttp
from aioia_core.settings import OpenAIAPISettings
from livekit import agents
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    ModelSettings,
    WorkerOptions,
    cli,
)
from livekit.agents.llm import ChatContext, FunctionTool, RawFunctionTool
from livekit.agents.types import NOT_GIVEN, NotGiven
from livekit.plugins import elevenlabs, openai, simli
from pydantic import ValidationError

from fancall.agent.call_timer import run_call_timer
from fancall.agent.phone_dialer import dial_phone
from fancall.agent.reply_limit import limit_sentences
from fancall.persona import DEFAULT_PERSONA, Persona
from fancall.prompts import (
    OPENING_INSTRUCTIONS,
    PHONE_OPENING_INSTRUCTIONS,
    compose_instructions,
)
from fancall.schemas import AgentDispatchRequest
from fancall.settings import (
    ElevenLabsSettings,
    FancallCallSettings,
    FancallModelSettings,
    LiveKitSettings,
    SimliSettings,
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
        opening_instructions: str = OPENING_INSTRUCTIONS,
        opening_message: str | None = None,
        **kwargs,
    ):
        super().__init__(instructions=instructions, **kwargs)
        self.opening_instructions = opening_instructions
        self.opening_message = opening_message

    async def on_enter(self) -> None:
        """Called when agent becomes active in the session."""
        # 호스트 앱이 첫 멘트를 주면 LLM 없이 그대로 읽는다.
        # 팬도 "여보세요"를 겹쳐 말하기 쉬우니 영상 첫인사처럼 끼어들 수 있게 둔다
        if self.opening_message:
            self.session.say(self.opening_message)
            return
        # 실제 통화처럼 캐릭터 말투로 먼저 인사한다 (영상: 소리·화면 확인, 전화: 여보세요)
        self.session.generate_reply(instructions=self.opening_instructions)

    def llm_node(
        self,
        chat_ctx: ChatContext,
        tools: list[FunctionTool | RawFunctionTool],
        model_settings: ModelSettings,
    ) -> AsyncIterator[Any]:
        """Generate the reply, cut to MAX_REPLY_SENTENCES before it is spoken."""
        reply = Agent.default.llm_node(self, chat_ctx, tools, model_settings)
        return limit_sentences(reply, MAX_REPLY_SENTENCES)


async def start_avatar(
    ctx: JobContext,
    session: AgentSession,
    avatar_id: str | None,
    livekit_settings: LiveKitSettings,
    simli_settings: SimliSettings,
    call_settings: FancallCallSettings,
) -> None:
    """
    Start a Simli lip-synced avatar that joins the room and speaks the agent's audio.

    Simli needs a pre-registered face (avatar_id) and an API key. Without them, or
    if the Simli API call fails, the call continues voice-only and the frontend
    shows the profile picture. Configuration or code errors are raised.
    """
    if not (avatar_id and simli_settings.api_key):
        logger.info("No Simli avatar configured for this persona; voice-only.")
        return

    # Once started, the agent's audio goes only to the Simli participant. If Simli
    # disconnects mid-call (defaults: 30s idle, 600s total), the fan loses the voice
    # too, so keep the avatar alive for the whole call including the goodbye.
    call_seconds = math.ceil(
        call_settings.call_duration_seconds + call_settings.closing_grace_seconds
    )
    logger.info("Starting Simli avatar with face_id: %s", avatar_id)
    avatar = simli.AvatarSession(
        simli_config=simli.SimliConfig(
            api_key=simli_settings.api_key,
            face_id=avatar_id,
            max_session_length=call_seconds,
            max_idle_time=call_seconds,
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
    except (aiohttp.ClientError, asyncio.TimeoutError):
        # Simli API errors (HTTP status, network, timeout) are expected outages
        logger.exception("Simli avatar failed to start; continuing voice-only.")


async def entrypoint(
    ctx: JobContext,
    default_persona: Persona,
    livekit_settings: LiveKitSettings,
    openai_settings: OpenAIAPISettings,  # pylint: disable=unused-argument
    elevenlabs_settings: ElevenLabsSettings,
    simli_settings: SimliSettings,
    model_settings: FancallModelSettings,
    call_settings: FancallCallSettings,
) -> None:
    """
    Agent entrypoint. Initializes AgentSession for text-to-speech tasks.

    Args:
        ctx: LiveKit job context
        default_persona: Default persona for fallback configuration
        livekit_settings: LiveKit settings; the avatar joins the room with these,
            and phone calls dial out through its SIP outbound trunk
        openai_settings: OpenAI API settings (현재 미사용: livekit.plugins.openai가 환경변수 직접 사용)
        elevenlabs_settings: ElevenLabs TTS settings
        simli_settings: Simli avatar settings
        model_settings: Fancall LLM/TTS model settings
        call_settings: Call timing settings (video and phone)
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

    phone_call = metadata.phone_call or metadata.phone_number is not None

    logger.info(
        "Agent configuration: avatar_id=%s, voice_id=%s, phone_call=%s",
        avatar_id,
        voice_id,
        phone_call,
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

    # 전화에는 화면이 없으므로 아바타를 띄우지 않는다
    if not phone_call:
        await start_avatar(
            ctx,
            session,
            avatar_id,
            livekit_settings,
            simli_settings,
            call_settings,
        )

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

    # 팬이 전화를 받은 뒤에 세션을 시작해야 첫인사가 허공에 나가지 않는다
    if metadata.phone_number:
        trunk_id = livekit_settings.sip_outbound_trunk_id
        if not trunk_id:
            logger.error("LIVEKIT_SIP_OUTBOUND_TRUNK_ID is required for phone calls")
            ctx.shutdown(reason="SIP outbound trunk is not configured")
            return
        answered = await dial_phone(
            ctx.api.sip, ctx.room.name, trunk_id, metadata.phone_number
        )
        if not answered:
            ctx.shutdown(reason="Phone call was not answered")
            return

    agent = CompanionAgent(
        instructions=instructions,
        opening_instructions=(
            PHONE_OPENING_INSTRUCTIONS if phone_call else OPENING_INSTRUCTIONS
        ),
        opening_message=metadata.opening_message,
    )
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
    simli_settings: SimliSettings,
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
        simli_settings: Simli avatar settings
        model_settings: Fancall LLM/TTS model settings
        call_settings: Call timing settings (video and phone)

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
            simli_settings=simli_settings,
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
    elevenlabs_settings = ElevenLabsSettings()
    simli_settings = SimliSettings()
    model_settings = FancallModelSettings()
    call_settings = FancallCallSettings()
    cli.run_app(
        create_worker_options(
            DEFAULT_PERSONA,
            livekit_settings,
            openai_settings,
            elevenlabs_settings,
            simli_settings,
            model_settings,
            call_settings,
        )
    )


if __name__ == "__main__":
    main()
