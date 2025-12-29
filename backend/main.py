"""
Standalone FastAPI application for Fancall.

This module provides the entry point for running Fancall as an independent service.

Usage:
    uvicorn main:app --reload

Environment Variables:
    DATABASE_URL: PostgreSQL database URL
    LIVEKIT_URL: LiveKit server URL
    LIVEKIT_API_KEY: LiveKit API key
    LIVEKIT_API_SECRET: LiveKit API secret
    JWT_SECRET_KEY: JWT secret key (default: dev-secret for development)
    LOG_LEVEL: Logging level (default: INFO)
"""

import logging
import os

from aioia_core.errors import (
    INTERNAL_SERVER_ERROR,
    VALIDATION_ERROR,
    ErrorResponse,
    extract_error_code_from_exception,
    get_error_detail_from_exception,
)
from aioia_core.models import Base
from aioia_core.settings import DatabaseSettings, JWTSettings
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from fancall.api.router import create_fancall_router
from fancall.factories import LiveRoomManagerFactory
from fancall.settings import LiveKitSettings

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ==============================================================================
# Initialize Settings from Environment Variables
# ==============================================================================

# BaseSettings automatically reads from environment variables
db_settings = DatabaseSettings()  # DATABASE_URL
livekit_settings = LiveKitSettings()  # LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET
jwt_settings = JWTSettings()  # JWT_SECRET_KEY

logger.info("Loaded settings from environment variables")
logger.info("LiveKit URL: %s", livekit_settings.url)
logger.info(
    "Database: %s", db_settings.url.rsplit("@", maxsplit=1)[-1]
)  # Hide credentials


# ==============================================================================
# Initialize Database
# ==============================================================================

engine = create_engine(db_settings.url, echo=False)
Base.metadata.create_all(engine)
db_session_factory = sessionmaker(bind=engine)

logger.info("Database initialized")


# Create FastAPI app
app = FastAPI(
    title="Fancall API",
    version="0.1.0",
    description="AI-powered video call with virtual companions",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# Error Handlers
# ==============================================================================


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTPException with consistent error response format."""
    error_code = extract_error_code_from_exception(exc)
    detail = get_error_detail_from_exception(exc)

    logger.warning(
        "HTTPException: %s %s | status=%d | code=%s",
        request.method,
        request.url,
        exc.status_code,
        error_code,
    )

    error_data = ErrorResponse(status=exc.status_code, detail=detail, code=error_code)
    return JSONResponse(status_code=exc.status_code, content=error_data.model_dump())


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    first_error = exc.errors()[0] if exc.errors() else {}
    field = (
        first_error.get("loc", ["unknown"])[-1] if first_error.get("loc") else "unknown"
    )

    detail = f"Validation error in field '{field}': {first_error.get('msg', 'Invalid value')}"

    logger.warning(
        "ValidationError: %s %s | errors=%s",
        request.method,
        request.url,
        exc.errors(),
    )

    error_data = ErrorResponse(status=422, detail=detail, code=VALIDATION_ERROR)
    return JSONResponse(status_code=422, content=error_data.model_dump())


@app.exception_handler(Exception)
async def internal_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(
        "Unexpected error: %s %s | exc=%r",
        request.method,
        request.url,
        exc,
        exc_info=True,
    )

    error_data = ErrorResponse(
        status=500,
        detail="Internal Server Error",
        code=INTERNAL_SERVER_ERROR,
    )
    return JSONResponse(status_code=500, content=error_data.model_dump())


# ==============================================================================
# Routes
# ==============================================================================

# Create and include Fancall router
fancall_router = create_fancall_router(
    livekit_settings=livekit_settings,
    jwt_settings=jwt_settings,
    db_session_factory=db_session_factory,
    manager_factory=LiveRoomManagerFactory(db_session_factory),
    user_info_provider=None,  # Standalone mode: no user authentication
)
app.include_router(fancall_router)

logger.info("Fancall router registered")


@app.get("/healthz", tags=["management"])
async def health_check():
    """
    Health check endpoint.

    Returns:
        dict: Status message
    """
    return {"status": "healthy", "service": "fancall"}


@app.get("/", tags=["management"])
async def root():
    """
    Root endpoint.

    Returns:
        dict: Welcome message with documentation link
    """
    return {
        "message": "Fancall API",
        "description": "AI-powered video call with virtual companions",
        "docs": "/docs",
    }
