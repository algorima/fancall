"""
Fancall settings
"""

from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings


class FancallModelSettings(BaseSettings):
    """Fancall LLM/TTS model settings."""

    openai_model: str = "gpt-4o-mini"
    # "none" keeps thinking models (e.g. Gemini via the OpenAI-compatible API) fast enough for a live call
    openai_reasoning_effort: (
        Literal["none", "minimal", "low", "medium", "high", "xhigh", "max"] | None
    ) = None
    elevenlabs_model: str = "eleven_flash_v2_5"

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
