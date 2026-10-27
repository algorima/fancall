"""
Fancall Pydantic schemas
"""

from datetime import datetime
from typing import Literal

from humps import camelize
from pydantic import BaseModel, ConfigDict, Field

from fancall.persona import Persona


class MemoryLine(BaseModel):
    """One line from an earlier call between this fan and this trainee."""

    model_config = ConfigDict(alias_generator=camelize, populate_by_name=True)

    speaker: Literal["fan", "idol"]
    text: str = Field(max_length=500)


class AgentDispatchRequest(Persona):
    """API dispatch 요청 스키마. Persona를 상속하여 확장 가능."""

    language: str | None = Field(
        default=None,
        description="Fan's app language code (e.g. 'en'); used for the opening greeting",
    )
    memory_key: str | None = Field(
        default=None,
        max_length=100,
        description="Host-chosen id of the trainee this call is with. For a signed-in "
        "fan, fancall loads the stored lines of earlier calls under this key into "
        "`memory` when none are passed.",
    )
    memory: list[MemoryLine] = Field(
        default_factory=list,
        max_length=200,
        description="Lines from earlier calls with this fan, oldest first. The host "
        "app stores them (per signed-in fan and trainee) and passes them back so the "
        "trainee remembers the fan.",
    )


class MemoryAppendRequest(BaseModel):
    """Lines to add to the signed-in fan's memory of one trainee."""

    model_config = ConfigDict(alias_generator=camelize, populate_by_name=True)

    memory_key: str = Field(min_length=1, max_length=100)
    lines: list[MemoryLine] = Field(max_length=50)


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
