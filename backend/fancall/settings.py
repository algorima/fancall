"""
Fancall settings
"""

from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings


class FancallModelSettings(BaseSettings):
    """Fancall LLM/TTS model settings."""

    openai_model: str = "gpt-4o-mini"
    # Where openai_model is served when it is not on OPENAI_BASE_URL, e.g. a fast
    # host like Cerebras ("https://api.cerebras.ai/v1"). The fallback model keeps
    # using OPENAI_BASE_URL / OPENAI_API_KEY. Empty: both use the environment.
    openai_base_url: str = ""
    openai_api_key: str = ""
    # "none" keeps thinking models (e.g. Gemini via the OpenAI-compatible API) fast enough for a live call
    openai_reasoning_effort: (
        Literal["none", "minimal", "low", "medium", "high", "xhigh", "max"] | None
    ) = None
    # Model to switch to when the first one has not answered within
    # openai_attempt_timeout (a 13s stall was seen on 2026-10-23). Empty: no fallback.
    openai_fallback_model: str = ""
    openai_attempt_timeout: float = 2.5
    # Most expressive realtime model; plays through the text-to-dialogue stream
    elevenlabs_model: str = "eleven_v4_turbo"
    # LiveKit Cloud TTS as "provider/model:voice" (e.g. "inworld/inworld-tts-1.5-mini:Timothy").
    # Empty uses ElevenLabs with the persona's voice; set it when ElevenLabs is unavailable.
    tts_model: str = ""
    # Language code for tts_model when the provider needs one (e.g. "ko", "en"). Empty: model default.
    tts_language: str = ""
    # Speaking-style instructions for providers that take them (Gemini TTS). Empty: none.
    tts_instructions: str = ""
    # Fan speech recognition through LiveKit Cloud. Flux decides when the fan has
    # finished speaking, so the reply can start without an extra silence wait.
    stt_model: str = "deepgram/flux-general-en"
    # Flux sends an early "probably done" signal at this confidence; the reply
    # starts generating then and is dropped if the fan keeps talking (0.3-0.9).
    stt_eager_eot_threshold: float = 0.4
    # Flux ends the fan's turn at this confidence (0.5-0.9, Flux default 0.7).
    stt_eot_threshold: float = 0.7

    class Config:
        env_prefix = "FANCALL_"


class FancallCallSettings(BaseSettings):
    """Video call timing settings.

    Attributes:
        call_duration_seconds: Total call length before the agent leaves.
        wrap_up_lead_seconds: Seconds before the end when the agent stops
            opening new topics and keeps answers short.
        closing_lead_seconds: Seconds before the end when the agent cuts in
            with a goodbye. Covers LLM·TTS latency plus a two-sentence goodbye.
        closing_grace_seconds: Extra seconds allowed past the end so the
            goodbye is not cut off mid-sentence.
        quiet_nudge_seconds: Seconds of silence (agent listening, fan not
            speaking) before the agent speaks first. The line opens with a
            prepared filler ("Hmm~"), heard about 1s later through the avatar,
            so it lands under 3s: in 295 real fan calls three quarters of
            pauses were under 2.9s. 1.5s leaves the fan room to answer first
            (median pause 1.38s); at 0.5s the trainee kept talking over a fan
            bot in a 2026-10-23 call. If the fan starts talking first, the line
            is dropped.
        quiet_after_question_seconds: Silence before speaking first when the
            agent's last line asked the fan something; the fan is expected to
            answer. A 2026-10-23 call with a fan bot showed the trainee asking
            six questions in a row with no room to answer.
        quiet_nudge_max_in_row: Times the agent speaks first before the fan
            replies again. 0 turns the nudge off. Real fan calls leave no long
            silences, so the trainee keeps the call going for a while.
        end_of_turn_min_delay: Extra wait after the speech recognizer decides
            the fan finished. Flux already decides end of turn, so keep it short.
        quick_reaction_rate: Share of LLM replies to the fan that open with a
            short reaction. Idols in real 영통팬싸 open 31.7% of replies with
            one (122 of 385) and still start the rest within 1.4s; our LLM
            replies start 2.5-3.5s after the fan without one (2026-10-23), a
            gap that reads as lag. So every LLM reply opens with one for now;
            set this back toward 0.317 once replies start within 1.4s on their
            own. Prepared fast replies never get one.
        fast_replies: Answer greetings, compliments, love and goodbyes with
            prepared lines from real calls instead of the LLM. Off: those
            lines can't pick up what the fan just said or get shy in context,
            which read as canned (2026-10-26), and the LLM's first word now
            comes within 0.5s.
    """

    call_duration_seconds: float = 180
    wrap_up_lead_seconds: float = 30
    closing_lead_seconds: float = 12
    closing_grace_seconds: float = 5
    quiet_nudge_seconds: float = 1.5
    quiet_nudge_max_in_row: int = 2
    quiet_after_question_seconds: float = 2.0
    end_of_turn_min_delay: float = 0.2
    quick_reaction_rate: float = 1.0
    fast_replies: bool = False

    class Config:
        env_prefix = "FANCALL_"

    @model_validator(mode="after")
    def check_timeline(self) -> "FancallCallSettings":
        """Validate that wrap-up and closing happen in order inside the call."""
        if not (
            self.call_duration_seconds
            > self.wrap_up_lead_seconds
            > self.closing_lead_seconds
            > 0
        ):
            raise ValueError(
                "Expected call_duration_seconds > wrap_up_lead_seconds "
                "> closing_lead_seconds > 0"
            )
        if self.closing_grace_seconds < 0:
            raise ValueError("closing_grace_seconds must not be negative")
        if self.quiet_nudge_seconds <= 0:
            raise ValueError("quiet_nudge_seconds must be positive")
        if self.quiet_nudge_max_in_row < 0:
            raise ValueError("quiet_nudge_max_in_row must not be negative")
        return self


class ElevenLabsSettings(BaseSettings):
    """Settings for ElevenLabs TTS

    Attributes:
        api_key: ElevenLabs API key (ELEVEN_API_KEY).
    """

    api_key: str | None = None

    class Config:
        env_prefix = "ELEVEN_"


class AvatarSettings(BaseSettings):
    """Settings for realtime lip-synced avatars (replaces discontinued Hedra)

    A provider is enabled by setting its API key. Anam is preferred when its key
    and avatar ID are set, then Tavus; otherwise Simli is used when the persona has an avatar_id (Simli face
    ID), and LemonSlice when only a profile_picture_url is available. With no key
    set, the call is voice-only.

    Attributes:
        anam_api_key: Anam API key (ANAM_API_KEY).
        anam_avatar_id: Anam avatar to render (ANAM_AVATAR_ID). Required for Anam.
        anam_video_width: Anam output width in pixels (ANAM_VIDEO_WIDTH).
        anam_video_height: Anam output height in pixels (ANAM_VIDEO_HEIGHT).
            Portrait by default to fill the 9:16 call screen.
        tavus_api_key: Tavus API key (TAVUS_API_KEY).
        tavus_face_id: Tavus face to render (TAVUS_FACE_ID). Stock face if unset.
        tavus_pal_id: Tavus PAL in echo mode (TAVUS_PAL_ID). Stock PAL if unset.
        simli_api_key: Simli API key (SIMLI_API_KEY).
        lemonslice_api_key: LemonSlice API key (LEMONSLICE_API_KEY).
    """

    anam_api_key: str | None = None
    anam_avatar_id: str | None = None
    anam_video_width: int = 768
    anam_video_height: int = 1152
    tavus_api_key: str | None = None
    tavus_face_id: str | None = None
    tavus_pal_id: str | None = None
    simli_api_key: str | None = None
    lemonslice_api_key: str | None = None


class LiveKitSettings(BaseSettings):
    """Settings for LiveKit API integration

    Attributes:
        url: LiveKit server WebSocket URL. Defaults to local dev server.
        api_key: LiveKit API key. Defaults to 'devkey' for local development.
        api_secret: LiveKit API secret. Defaults to 'secret' for local development.
        agent_name: Agent name for LiveKit dispatch. Defaults to 'fancall'.
    """

    url: str = "ws://localhost:7880"  # Local LiveKit dev server
    api_key: str = "devkey"  # Default API key for local dev
    api_secret: str = "secret"  # Default API secret for local dev
    agent_name: str = "fancall"  # Agent name for LiveKit dispatch

    class Config:
        env_prefix = "LIVEKIT_"

    @model_validator(mode="after")
    def check_credentials(self) -> "LiveKitSettings":
        """Validate that all credentials are provided together when overriding defaults."""
        credential_fields = {"url", "api_key", "api_secret"}
        provided_credential_fields = self.model_fields_set.intersection(
            credential_fields
        )

        if 0 < len(provided_credential_fields) < len(credential_fields):
            raise ValueError(
                "All LiveKit credentials (URL, API key, and API secret) must be provided together when overriding defaults."
            )
        return self
