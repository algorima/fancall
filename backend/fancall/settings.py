"""
Fancall settings
"""

from pydantic import root_validator
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

    @root_validator(skip_on_failure=True)
    def check_credentials(cls, values):  # pylint: disable=no-self-argument
        """Validate that all credentials are present together."""
        url = values.get("url")
        api_key = values.get("api_key")
        api_secret = values.get("api_secret")

        if any([url, api_key, api_secret]) and not all([url, api_key, api_secret]):
            raise ValueError(
                "All LiveKit credentials (URL, API key, and API secret) must be provided together."
            )
        return values
