"""
Fancall Pydantic schemas
"""

from datetime import datetime

from humps import camelize
from pydantic import BaseModel, ConfigDict

from fancall.persona import AgentPersona


class AgentDispatchRequest(AgentPersona):
    """API dispatch 요청 스키마. AgentPersona를 상속하여 확장 가능."""


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
