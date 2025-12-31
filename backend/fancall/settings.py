"""
Fancall settings
"""

from pydantic import model_validator
from pydantic_settings import BaseSettings


class FancallModelSettings(BaseSettings):
    """Fancall LLM model settings."""

    openai_model: str = "gpt-4o-mini"

    class Config:
        env_prefix = "FANCALL_"


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
