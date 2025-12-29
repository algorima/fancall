"""
LiveKit service for fancall module
"""

import logging
from dataclasses import dataclass

from livekit import api
from livekit.protocol.agent_dispatch import CreateAgentDispatchRequest

from fancall.schemas import AgentDispatchRequest
from fancall.settings import LiveKitSettings

logger = logging.getLogger(__name__)


@dataclass
class LiveKitTokenResponse:
    """Structured response from the LiveKit Token generation"""

    token: str
    room_name: str
    identity: str


@dataclass
class LiveKitDispatchResponse:
    """Structured response from the LiveKit Agent Dispatch"""

    dispatch_id: str
    room_name: str
    agent_name: str


class LiveKitService:
    """Service for LiveKit operations including token generation and agent dispatch"""

    def __init__(self, livekit_settings: LiveKitSettings):
        """
        Initialize the LiveKit service with LiveKit settings.

        Args:
            livekit_settings: LiveKit settings containing required credentials
        """
        self.settings = livekit_settings

    def generate_token(
        self, user_id: str, name: str, room_name: str
    ) -> LiveKitTokenResponse | None:
        """
        Generate a LiveKit access token for a user to join a room.

        Args:
            user_id: User ID to use as identity
            name: Display name for the user
            room_name: Name of the room the user wants to join

        Returns:
            LiveKitTokenResponse object with token and room details, or None if the service is not configured.

        Raises:
            ValueError: If required parameters are missing
            Exception: If there's an error generating the token
        """
        if not self.settings.api_key or not self.settings.api_secret:
            logger.error("LiveKit credentials are not configured")
            return None

        if not user_id:
            raise ValueError("User ID is required to generate token")

        if not room_name:
            raise ValueError("Room name is required to generate token")

        try:
            logger.info(
                "Generating LiveKit token for user '%s' (identity: %s) to join room '%s'",
                name,
                user_id,
                room_name,
            )

            # Generate access token
            token = (
                api.AccessToken(self.settings.api_key, self.settings.api_secret)
                .with_identity(user_id)
                .with_name(name)
                .with_grants(
                    api.VideoGrants(
                        room_join=True,
                        room=room_name,
                        can_publish=True,
                        can_subscribe=True,
                    )
                )
                .to_jwt()
            )

            logger.info(
                "Successfully generated LiveKit token for user '%s' to join room '%s'",
                user_id,
                room_name,
            )

            return LiveKitTokenResponse(
                token=token, room_name=room_name, identity=user_id
            )

        except Exception as e:
            logger.error(
                "Error generating LiveKit token for user '%s' to join room '%s': %s",
                user_id,
                room_name,
                e,
            )
            raise

    async def dispatch_agent(
        self, request: AgentDispatchRequest, room_name: str
    ) -> LiveKitDispatchResponse | None:
        """
        Dispatch an agent with the given specification to a LiveKit room.

        Args:
            request: AgentDispatchRequest containing agent configuration
            room_name: Name of the room to dispatch the agent to

        Returns:
            LiveKitDispatchResponse object with dispatch details, or None if the service is not configured.

        Raises:
            Exception: If there's an error dispatching the agent
        """
        if (
            not self.settings.url
            or not self.settings.api_key
            or not self.settings.api_secret
        ):
            logger.error("LiveKit credentials are not configured")
            return None

        # Create client for this request
        async with api.LiveKitAPI(
            url=self.settings.url,
            api_key=self.settings.api_key,
            api_secret=self.settings.api_secret,
        ) as livekit_client:
            try:
                # Prepare metadata for the agent
                metadata_json = request.model_dump_json(exclude_none=True)

                logger.info(
                    "Dispatching agent '%s' to room '%s' with metadata: %s",
                    self.settings.agent_name,
                    room_name,
                    metadata_json,
                )

                # Create agent dispatch
                dispatch = await livekit_client.agent_dispatch.create_dispatch(
                    CreateAgentDispatchRequest(
                        agent_name=self.settings.agent_name,
                        room=room_name,
                        metadata=metadata_json,
                    )
                )

                logger.info(
                    "Successfully dispatched agent to room '%s' with dispatch_id: %s",
                    room_name,
                    dispatch.id,
                )

                return LiveKitDispatchResponse(
                    dispatch_id=dispatch.id,
                    room_name=room_name,
                    agent_name=self.settings.agent_name,
                )

            except Exception as e:
                logger.error("Error dispatching agent to room '%s': %s", room_name, e)
                raise
