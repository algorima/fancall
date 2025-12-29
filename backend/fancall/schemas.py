"""
Fancall Pydantic schemas
"""

from datetime import datetime

from humps import camelize
from pydantic import BaseModel, ConfigDict, Field


class AgentDispatchRequest(BaseModel):
    """Type-safe specification for LiveKit agent dispatch."""

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
        description="Custom system prompt for the agent",
    )


# LiveRoom schemas
class LiveRoomBase(BaseModel):
    """LiveRoom base model with common fields"""

    model_config = ConfigDict(alias_generator=camelize, populate_by_name=True)


class LiveRoomCreate(LiveRoomBase):
    """LiveRoom creation model - used in requests"""


class LiveRoomUpdate(BaseModel):
    """LiveRoom update model - used for partial update requests"""

    model_config = ConfigDict(alias_generator=camelize, populate_by_name=True)


class LiveRoom(LiveRoomBase):
    """LiveRoom complete model - used in responses"""

    id: str
    created_at: datetime
    updated_at: datetime


# API Response schemas
class TokenResponse(BaseModel):
    """Response with generated token"""

    model_config = ConfigDict(alias_generator=camelize, populate_by_name=True)

    token: str
    room_name: str
    identity: str


class DispatchResponse(BaseModel):
    """Response after dispatching agent"""

    model_config = ConfigDict(alias_generator=camelize, populate_by_name=True)

    dispatch_id: str
    room_name: str
    agent_name: str
