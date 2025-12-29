"""
Agent persona for Fancall.

This module defines the AgentPersona domain model and the default persona
used when no custom configuration is provided during dispatch.
Host applications can inject their own persona via LiveKitService constructor.
"""

from humps import camelize
from pydantic import BaseModel, ConfigDict, Field


class AgentPersona(BaseModel):
    """Agent의 정체성을 정의하는 도메인 모델."""

    model_config = ConfigDict(
        alias_generator=camelize, populate_by_name=True, extra="ignore"
    )

    avatar_id: str | None = Field(
        default=None, description="Hedra avatar ID for visual representation"
    )
    profile_picture_url: str | None = Field(
        default=None, description="Profile picture URL for avatar generation"
    )
    idle_video_url: str | None = Field(
        default=None, description="Video to display during idle periods"
    )
    voice_id: str | None = Field(
        default=None, description="Fish Audio voice ID for TTS"
    )
    system_prompt: str | None = Field(
        default=None,
        description="System prompt for the agent",
    )


DEFAULT_PERSONA = AgentPersona()
