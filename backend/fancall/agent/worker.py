#!/usr/bin/env python3
"""
LiveKit Agent Worker with ElevenLabs TTS Integration

This file runs a real-time AI agent using ElevenLabs TTS and, when configured,
a lip-synced avatar (Anam, Tavus, Simli or LemonSlice).
"""

import asyncio
import logging
import os
from collections.abc import AsyncIterable, AsyncIterator
from functools import partial
from pathlib import Path
from typing import Any

from aioia_core.settings import HedraSettings, OpenAIAPISettings
from livekit import agents, rtc
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    ModelSettings,
    WorkerOptions,
    cli,
    inference,
)
from livekit.agents.llm import LLM, ChatContext, ChatMessage, FallbackAdapter, Tool
from livekit.agents.types import NOT_GIVEN
from livekit.plugins import anam, elevenlabs, lemonslice, openai, simli, tavus
from pydantic import ValidationError

from fancall.agent.avatar import (
    FakeRenderer,
    IdleClip,
    RenderedVideoGenerator,
    Renderer,
    WebSocketRenderer,
    start_rendered_avatar,
)
from fancall.agent.call_timer import run_call_timer
from fancall.agent.fast_reply import FastReplies
from fancall.agent.hangup import end_call_when_fan_leaves
from fancall.agent.latency_log import log_latency
from fancall.agent.quick_reaction import (
    REACTION_RATE,
    REACTION_SAMPLE_RATE,
    QuickReactions,
    ReactionFetch,
    cached_fetch,
    elevenlabs_pcm_fetch,
    prepend,
    prerender,
    strip_prefix,
    tts_pcm_fetch,
)
from fancall.agent.quiet_nudge import QuietNudger
from fancall.agent.reply_limit import drop_opening_interjection, limit_sentences
from fancall.persona import DEFAULT_PERSONA, Persona
from fancall.prompts import (
    AI_HONESTY_NOTE,
    OPENING_INSTRUCTIONS,
    QUICK_REACTION_NOTE,
    QUIET_NUDGE_USER_INPUT,
    compose_instructions,
    language_note,
    memory_note,
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
# Prepared reactions and replies, kept so each voice synthesizes each line once
PRERENDER_CACHE_DIR = Path(
    os.environ.get("FANCALL_PRERENDER_CACHE", Path.home() / ".cache/fancall/prerender")
)


async def _nothing() -> AsyncIterator[Any]:
    return
    yield  # pragma: no cover


class CompanionAgent(Agent):
    """
    A voice-enabled AI companion agent.
    Processes user input and generates conversational responses using LLM and TTS.
    """

    def __init__(
        self,
        instructions: str = DEFAULT_SYSTEM_PROMPT,
        language: str | None = None,
        prepared_fetch: ReactionFetch | None = None,
        prepared_sample_rate: int = REACTION_SAMPLE_RATE,
        reaction_rate: float = REACTION_RATE,
        fast_replies: bool = True,
        **kwargs,
    ):
        super().__init__(instructions=instructions, **kwargs)
        self._language = language
        self._reactions = QuickReactions(language, rate=reaction_rate)
        self._prepared_fetch = prepared_fetch
        self._prepared_sample_rate = prepared_sample_rate
        self._prepared_audio: dict[str, list[rtc.AudioFrame]] = {}
        self._prerender_task: asyncio.Task[None] | None = None
        self._fan_spoke = False
        self._pending_prepared: str | None = None
        self._fast_replies = FastReplies(language) if fast_replies else None

    async def on_enter(self) -> None:
        """Called when agent becomes active in the session."""
        # 맞장구와 바로 대답은 미리 음성으로 만들어 두고 TTS 없이 바로 낸다
        self._prerender_task = asyncio.create_task(self._prerender())
        self.session.on("user_input_transcribed", self._note_fan_speech)
        # 실제 영통처럼 소리·화면 확인과 인사로 먼저 말을 건다
        self.session.generate_reply(
            user_input=opening_user_input(self._language),
            instructions=OPENING_INSTRUCTIONS,
        )

    def _note_fan_speech(self, event: Any) -> None:
        # 팬이 말했으면 다음 대답은 팬 말에 대한 대답이다 (먼저 거는 한마디와 구분)
        if event.transcript.strip():
            self._fan_spoke = True

    def tts_node(
        self, text: AsyncIterable[str], model_settings: ModelSettings
    ) -> AsyncIterator[rtc.AudioFrame]:
        """Play the prepared part llm_node put first from its audio, then the rest."""
        prepared, self._pending_prepared = self._pending_prepared, None
        frames = self._prepared_audio.get(prepared, []) if prepared else []
        if not frames:
            return Agent.default.tts_node(self, text, model_settings)
        assert prepared is not None
        rest = strip_prefix(text, prepared)
        return prepend(frames, Agent.default.tts_node(self, rest, model_settings))

    async def _prerender(self) -> None:
        if self._prepared_fetch is not None:
            texts = self._reactions.words + (
                self._fast_replies.lines if self._fast_replies else ()
            )
            self._prepared_audio = await prerender(
                self._prepared_fetch, texts, self._prepared_sample_rate
            )
            logger.info(
                "Prerendered %d/%d lines", len(self._prepared_audio), len(texts)
            )

    def llm_node(
        self,
        chat_ctx: ChatContext,
        tools: list[Tool],
        model_settings: ModelSettings,
    ) -> AsyncIterator[Any]:
        """Reply to the fan, starting from prepared audio where it can.

        LiveKit starts speech synthesis only on the first text, and with
        preemptive generation this runs as soon as the fan seems done. So text
        sent first here plays right after the fan's turn, from prepared audio
        (tts_node swaps it in):
        - a set-phrase fan line (greeting, compliment, love, goodbye) gets a
          prepared reply and no LLM call at all;
        - otherwise the reply may open with a short reaction while the LLM
          writes the rest, cut to MAX_REPLY_SENTENCES;
        - a line the trainee says first after a pause opens with a filler
          ("Hmm~", "Oh, right~").
        """
        fan_spoke, self._fan_spoke = self._fan_spoke, False
        last_user = _last_user_text(chat_ctx)
        fan_line = last_user if fan_spoke else ""
        line = (
            self._fast_replies.pick(fan_line)
            if self._fast_replies and fan_line
            else None
        )
        if line and line in self._prepared_audio:
            logger.info("Fast reply %r", line)
            self._pending_prepared = line
            return prepend([line], _nothing())
        reply = limit_sentences(
            Agent.default.llm_node(self, chat_ctx, tools, model_settings),
            MAX_REPLY_SENTENCES,
        )
        if last_user == QUIET_NUDGE_USER_INPUT:
            reaction: str | None = self._reactions.filler()
        else:
            reaction = self._reactions.pick(fan_line) if fan_line else None
        if not reaction or reaction not in self._prepared_audio:
            return reply
        logger.info("Reacting %r", reaction)
        self._pending_prepared = reaction
        return prepend([reaction + " "], drop_opening_interjection(reply))


async def _wait_until_idle(session: AgentSession) -> None:
    """Wait until the trainee is listening and the fan is not talking."""
    while not (session.agent_state == "listening" and session.user_state != "speaking"):
        await asyncio.sleep(0.2)


def _last_user_text(chat_ctx: ChatContext) -> str:
    for item in reversed(chat_ctx.items):
        if isinstance(item, ChatMessage) and item.role == "user":
            return item.text_content or ""
    return ""


def _tell_nudger(nudger: QuietNudger, ev: Any) -> None:
    """Pass who said what to the nudger (fan replies reset it, questions slow it)."""
    if not isinstance(ev.item, ChatMessage):
        return
    if ev.item.role == "user":
        nudger.on_user_message(ev.item.text_content or "")
    elif ev.item.role == "assistant":
        nudger.on_agent_message(ev.item.text_content or "")
        logger.info("Trainee said: %s", (ev.item.text_content or "")[:300])


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


# The room hears the trainee at this rate; TTS audio is resampled to it
RENDER_OUTPUT_SAMPLE_RATE = 24_000


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
    if avatar_settings.render_url or avatar_settings.render_idle_dir:
        try:
            await start_self_rendered_avatar(
                ctx, session, profile_picture_url, avatar_settings
            )
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception("Rendered avatar failed to start; continuing voice-only.")
        return

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


async def start_self_rendered_avatar(
    ctx: JobContext,
    session: AgentSession,
    profile_picture_url: str | None,
    avatar_settings: AvatarSettings,
) -> None:
    """Draw the face on our own GPU render server, or from an idle clip without one."""
    size = (avatar_settings.render_width, avatar_settings.render_height)
    if avatar_settings.render_url:
        photo = (
            profile_picture_url
            if profile_picture_url and profile_picture_url.startswith("http")
            else avatar_settings.render_photo
        )
        if not photo:
            raise ValueError(
                "RENDER_PHOTO or an http profile picture is needed to render the face"
            )
        logger.info("Starting rendered avatar on %s", avatar_settings.render_url)
        renderer: Renderer = WebSocketRenderer(
            avatar_settings.render_url,
            photo,
            size=size,
            layout=avatar_settings.render_layout,
        )
        generator = RenderedVideoGenerator(
            renderer, output_sample_rate=RENDER_OUTPUT_SAMPLE_RATE
        )
    else:
        assert avatar_settings.render_idle_dir is not None
        logger.info(
            "Starting idle-clip avatar from %s (no GPU)",
            avatar_settings.render_idle_dir,
        )
        idle = IdleClip.load(avatar_settings.render_idle_dir, size=size)
        generator = RenderedVideoGenerator(
            FakeRenderer(idle.frame(0)),
            idle=idle,
            output_sample_rate=RENDER_OUTPUT_SAMPLE_RATE,
        )
    await start_rendered_avatar(
        session,
        ctx.room,
        generator,
        size=size,
        output_sample_rate=RENDER_OUTPUT_SAMPLE_RATE,
    )


def _build_llm(model_settings: FancallModelSettings) -> LLM:
    """The reply model, falling back to a second one when the first stalls."""
    reasoning_effort = model_settings.openai_reasoning_effort or NOT_GIVEN
    llms: list[LLM] = [
        openai.LLM(
            model=model_settings.openai_model,
            base_url=model_settings.openai_base_url or NOT_GIVEN,
            api_key=model_settings.openai_api_key or NOT_GIVEN,
            reasoning_effort=reasoning_effort,
        )
    ]
    if model_settings.openai_fallback_model:
        llms.append(
            openai.LLM(
                model=model_settings.openai_fallback_model,
                reasoning_effort=reasoning_effort,
            )
        )
    # 첫 모델이 멈추면 대답이 통째로 늦어지므로 다른 모델로 넘어간다
    return (
        FallbackAdapter(llms, attempt_timeout=model_settings.openai_attempt_timeout)
        if len(llms) > 1
        else llms[0]
    )


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
    llm = _build_llm(model_settings)
    if voice_id:
        logger.info("Using ElevenLabs voice_id: %s", voice_id)

    tts = (
        inference.TTS(model_settings.tts_model)
        if model_settings.tts_model
        else elevenlabs.TTS(
            api_key=elevenlabs_settings.api_key or NOT_GIVEN,
            model=model_settings.elevenlabs_model,
            voice_id=voice_id or elevenlabs.DEFAULT_VOICE_ID,
        )
    )

    # 팬이 말로 대화한다. Flux가 말 끝을 판단하고, 답은 그 전에 미리 만들어 둔다
    # (실제 영통팬싸 말 사이 쉼 중앙값 1.4초: docs/call-naturalness-criteria.md)
    session: AgentSession = AgentSession(
        llm=llm,
        tts=tts,
        stt=inference.STT(
            model_settings.stt_model,
            extra_kwargs=(
                {
                    "eager_eot_threshold": model_settings.stt_eager_eot_threshold,
                    "eot_threshold": model_settings.stt_eot_threshold,
                }
                if "flux" in model_settings.stt_model
                else NOT_GIVEN
            ),
        ),
        turn_handling={
            "turn_detection": "stt",
            # Flux가 이미 말 끝을 판단하므로 기본 0.5초 추가 대기를 줄인다
            "endpointing": {"min_delay": call_settings.end_of_turn_min_delay},
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
    instructions = (
        compose_instructions(
            system_prompt, include_role_playing=False, include_video_call=True
        )
        + "\n\n"
        + QUICK_REACTION_NOTE
        + "\n\n"
        + memory_note([(line.speaker, line.text) for line in metadata.memory])
        + "\n\n"
        + language_note(metadata.language)
        + "\n\n"
        + AI_HONESTY_NOTE
    )
    logger.info(
        "Using instructions: %s",
        instructions[:100] + "..." if len(instructions) > 100 else instructions,
    )

    # 맞장구와 바로 대답은 통화 TTS와 같은 목소리·같은 샘플레이트로 미리 만들어 디스크에 둔다.
    # ElevenLabs는 LiveKit 플러그인으로 만들면 job이 죽어서(exit -11) REST로 받는다.
    eleven_key = elevenlabs_settings.api_key or os.environ.get("ELEVEN_API_KEY")
    reaction_fetch: ReactionFetch | None = None
    voice_key = ""
    if model_settings.tts_model:
        # 통화 TTS와 같은 연결을 쓰면 첫 인사가 미리 만들기 뒤에 줄을 선다 (33초 늦은 인사, 2026-10-23)
        reaction_fetch = tts_pcm_fetch(inference.TTS(model_settings.tts_model))
        voice_key = model_settings.tts_model
    elif eleven_key:
        reaction_fetch = elevenlabs_pcm_fetch(
            eleven_key,
            voice_id or elevenlabs.DEFAULT_VOICE_ID,
            model_settings.elevenlabs_model,
            tts.sample_rate,
        )
        voice_key = f"{model_settings.elevenlabs_model}:{voice_id}"
    if reaction_fetch is not None:
        reaction_fetch = cached_fetch(
            reaction_fetch,
            PRERENDER_CACHE_DIR,
            f"{voice_key}:{tts.sample_rate}",
            before_fetch=partial(_wait_until_idle, session),
        )
    agent = CompanionAgent(
        instructions=instructions,
        language=metadata.language,
        prepared_fetch=reaction_fetch,
        prepared_sample_rate=tts.sample_rate,
        reaction_rate=call_settings.quick_reaction_rate,
        fast_replies=call_settings.fast_replies,
    )

    # 팬이 조용하면 먼저 한마디 한다. 마무리 단계부터는 작별 인사와 겹치지 않게 멈춘다.
    nudger = QuietNudger(
        session,
        quiet_seconds=call_settings.quiet_nudge_seconds,
        max_in_row=call_settings.quiet_nudge_max_in_row,
        quiet_after_question_seconds=call_settings.quiet_after_question_seconds,
    )
    session.on("agent_state_changed", lambda ev: nudger.on_agent_state(ev.new_state))
    session.on("user_state_changed", lambda ev: nudger.on_user_state(ev.new_state))
    log_latency(session)

    session.on("conversation_item_added", partial(_tell_nudger, nudger))
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
