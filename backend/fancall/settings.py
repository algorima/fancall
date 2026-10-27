"""
Fancall settings
"""

from openai.types.shared import ReasoningEffort
from pydantic import model_validator
from pydantic_settings import BaseSettings


class FancallModelSettings(BaseSettings):
    """Fancall LLM/TTS model settings."""

    openai_model: str = "gpt-4o-mini"
    # Unset keeps the plugin default. Thinking models need a low effort to answer
    # fast enough for a live call. Allowed values follow the installed openai SDK
    openai_reasoning_effort: ReasoningEffort = None
    elevenlabs_model: str = "eleven_flash_v2_5"
    stt_model: str = "gpt-4o-mini-transcribe"  # Phone calls only
    stt_language: str = "ko"  # Phone calls only

    class Config:
        env_prefix = "FANCALL_"


class FancallCallSettings(BaseSettings):
    """Call timing settings, shared by video and phone calls.

    Attributes:
        call_duration_seconds: Total call length before the agent leaves.
        wrap_up_lead_seconds: Seconds before the end when the agent stops
            opening new topics and keeps answers short.
        closing_lead_seconds: Seconds before the end when the agent cuts in
            with a goodbye. Covers LLM·TTS latency plus a two-sentence goodbye.
        closing_grace_seconds: Extra seconds allowed past the end so the
            goodbye is not cut off mid-sentence.
    """

    call_duration_seconds: float = 180
    wrap_up_lead_seconds: float = 30
    closing_lead_seconds: float = 12
    closing_grace_seconds: float = 5

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
        return self


class ElevenLabsSettings(BaseSettings):
    """Settings for ElevenLabs TTS

    Attributes:
        api_key: ElevenLabs API key (ELEVEN_API_KEY).
    """

    api_key: str | None = None

    class Config:
        env_prefix = "ELEVEN_"


class CorsSettings(BaseSettings):
    """CORS settings for the API server.

    The frontend fetches with ``credentials: "include"``, so browsers reject a
    wildcard origin and every allowed origin must be listed explicitly.

    Attributes:
        allowed_origins: Comma-separated list of origins allowed to make
            credentialed requests (CORS_ALLOWED_ORIGINS). Defaults to the local
            Next.js dev server.
    """

    allowed_origins: str = "http://localhost:3000"

    class Config:
        env_prefix = "CORS_"

    @property
    def origins(self) -> list[str]:
        """Parsed list of allowed origins; blank entries are ignored."""
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


class SimliSettings(BaseSettings):
    """Settings for the Simli realtime lip-synced avatar (replaces discontinued Hedra)

    The avatar is enabled when the API key is set and the persona has an avatar_id
    (Simli face ID). Otherwise the call is voice-only.

    Attributes:
        api_key: Simli API key (SIMLI_API_KEY).
    """

    api_key: str | None = None

    class Config:
        env_prefix = "SIMLI_"


class LiveKitSettings(BaseSettings):
    """Settings for LiveKit API integration

    Attributes:
        url: LiveKit server WebSocket URL. Defaults to local dev server.
        api_key: LiveKit API key. Defaults to 'devkey' for local development.
        api_secret: LiveKit API secret. Defaults to 'secret' for local development.
        agent_name: Agent name for LiveKit dispatch. Defaults to 'fancall'.
        sip_outbound_trunk_id: LiveKit SIP outbound trunk used to call phones.
            Phone calls are disabled when unset.
    """

    url: str = "ws://localhost:7880"  # Local LiveKit dev server
    api_key: str = "devkey"  # Default API key for local dev
    api_secret: str = "secret"  # Default API secret for local dev
    agent_name: str = "fancall"  # Agent name for LiveKit dispatch
    sip_outbound_trunk_id: str | None = None

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
