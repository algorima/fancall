"""
Fancall API router
"""

import uuid

from aioia_core.auth import UserInfoProvider
from aioia_core.errors import (
    INTERNAL_SERVER_ERROR,
    RESOURCE_NOT_FOUND,
    UNAUTHORIZED,
    ErrorResponse,
)
from aioia_core.fastapi import BaseCrudRouter
from aioia_core.settings import JWTSettings
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import sessionmaker

from fancall.factories import LiveRoomRepositoryFactory
from fancall.repositories.live_room_repository import DatabaseLiveRoomRepository
from fancall.schemas import (
    AgentDispatchRequest,
    DispatchResponse,
    LiveRoom,
    LiveRoomCreate,
    LiveRoomUpdate,
    TokenResponse,
)
from fancall.services.livekit_service import LiveKitService
from fancall.settings import LiveKitSettings


class LiveRoomRouter(
    BaseCrudRouter[LiveRoom, LiveRoomCreate, LiveRoomUpdate, DatabaseLiveRoomRepository]
):
    """Router for LiveRoom with LiveKit integration"""

    def __init__(
        self,
        livekit_settings: LiveKitSettings,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.livekit_settings = livekit_settings

    def _register_routes(self) -> None:
        """Register routes, allowing authenticated users to create rooms"""

        def require_authenticated_user(
            user_id: str | None = Depends(self.get_current_user_id_dep),
        ) -> str:
            """Require authenticated user for create operation."""
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "detail": "Authentication required to create a live room",
                        "code": UNAUTHORIZED,
                    },
                )
            return user_id

        # Use base class's create route with authenticated user requirement
        super()._register_create_route(auth_dependency=require_authenticated_user)

        self._register_token_route()  # POST /live-rooms/{id}/token
        self._register_dispatch_route()  # POST /live-rooms/{id}/dispatch

    def _register_token_route(self) -> None:
        """POST /live-rooms/{id}/token - Generate user access token"""

        @self.router.post(
            f"/{self.resource_name}/{{room_id}}/token",
            response_model=TokenResponse,
            summary="Generate User Access Token",
            responses={
                401: {"model": ErrorResponse},
                404: {"model": ErrorResponse},
                500: {"model": ErrorResponse},
            },
        )
        async def generate_token(
            room_id: str,
            user_id: str | None = Depends(self.get_current_user_id_dep),
            db_session=Depends(self.get_db_dep),
            repository: DatabaseLiveRoomRepository = Depends(self.get_repository_dep),
        ):
            # Verify room exists
            live_room = repository.get_by_id(room_id)
            if not live_room:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "detail": f"Live room not found: {room_id}",
                        "code": RESOURCE_NOT_FOUND,
                    },
                )

            # Determine identity and display name based on authentication
            identity: str
            display_name: str

            if user_id:
                # Authenticated user (provider guaranteed by startup validation)
                identity = user_id

                # Get user info (follows aioia-core pattern)
                assert (
                    self.user_info_provider
                ), "user_info_provider must be set (startup validation failed)"
                user_info = self.user_info_provider.get_user_info(user_id, db_session)
                if user_info is None:
                    # User not found in database - authentication/data inconsistency
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail={
                            "detail": "User not found",
                            "code": UNAUTHORIZED,
                        },
                    )

                # Use nickname if available, otherwise username, otherwise user_id
                display_name = user_info.nickname or user_info.username or user_id
            else:
                # Anonymous user: generate temporary identity
                identity = f"guest-{uuid.uuid4()}"
                display_name = "Guest"

            # Generate token
            livekit_service = LiveKitService(self.livekit_settings)
            token_response = livekit_service.generate_token(
                user_id=identity,
                name=display_name,
                room_name=room_id,
            )
            if not token_response:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "detail": "Failed to generate token",
                        "code": INTERNAL_SERVER_ERROR,
                    },
                )

            return TokenResponse(
                token=token_response.token,
                room_name=token_response.room_name,
                identity=token_response.identity,
            )

    def _register_dispatch_route(self) -> None:
        """POST /live-rooms/{id}/dispatch - Dispatch agent (generic)"""

        @self.router.post(
            f"/{self.resource_name}/{{room_id}}/dispatch",
            response_model=DispatchResponse,
            summary="Dispatch Agent",
            responses={
                404: {"model": ErrorResponse},
                500: {"model": ErrorResponse},
            },
        )
        async def dispatch_agent(
            room_id: str,
            request: AgentDispatchRequest,
            repository: DatabaseLiveRoomRepository = Depends(self.get_repository_dep),
        ):
            # Verify room exists
            live_room = repository.get_by_id(room_id)
            if not live_room:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "detail": f"Live room not found: {room_id}",
                        "code": RESOURCE_NOT_FOUND,
                    },
                )

            # Dispatch agent
            livekit_service = LiveKitService(self.livekit_settings)
            dispatch_response = await livekit_service.dispatch_agent(request, room_id)
            if not dispatch_response:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "detail": "Failed to dispatch agent",
                        "code": INTERNAL_SERVER_ERROR,
                    },
                )

            return DispatchResponse(
                dispatch_id=dispatch_response.dispatch_id,
                room_name=dispatch_response.room_name,
                agent_name=dispatch_response.agent_name,
            )


def create_fancall_router(
    livekit_settings: LiveKitSettings,
    jwt_settings: JWTSettings,
    db_session_factory: sessionmaker,
    repository_factory: LiveRoomRepositoryFactory,
    user_info_provider: UserInfoProvider | None = None,
    resource_name: str = "live-rooms",
    tags: list[str] | None = None,
) -> APIRouter:
    """
    Create fancall router with Settings-only injection pattern.

    Args:
        livekit_settings: LiveKit settings
        jwt_settings: JWT settings for authentication
        db_session_factory: Database session factory
        repository_factory: LiveRoom repository factory
        user_info_provider: Optional user info provider
        resource_name: Resource name for routes (default: "live-rooms")
        tags: Optional OpenAPI tags

    Returns:
        FastAPI APIRouter instance
    """
    router = LiveRoomRouter(
        livekit_settings=livekit_settings,
        model_class=LiveRoom,
        create_schema=LiveRoomCreate,
        update_schema=LiveRoomUpdate,
        db_session_factory=db_session_factory,
        repository_factory=repository_factory,
        user_info_provider=user_info_provider,
        jwt_secret_key=jwt_settings.secret_key,
        resource_name=resource_name,
        tags=tags or ["Fancall"],
    )
    return router.get_router()
