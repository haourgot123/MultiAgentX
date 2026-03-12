import asyncio

import uvicorn
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.api.data_ingestion.view import router as data_ingestion_router
from backend.api.files.view import router as file_router
from backend.api.conversation.view import router as conversation_router
from backend.api.meta.view import router as meta_router
from backend.api.revision.view import database_router
from backend.api.token.view import router as token_router
from backend.api.user.view import router as user_router
from backend.config.settings import _settings
from backend.exceptions.handler import exception_handler, global_exception_handler
from backend.exceptions.model import BusinessBaseException
from backend.middleware import (
    RateLimitMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from backend.realtime.socketio import socketio_manager
from backend.utils.logging import configure_logging

configure_logging()
logger.bind(service="app-startup").info("Backend logger configured")

main_router = APIRouter(prefix="/api")
main_router.include_router(token_router)
main_router.include_router(database_router)
main_router.include_router(user_router)
main_router.include_router(meta_router)
main_router.include_router(file_router)
main_router.include_router(conversation_router)
main_router.include_router(data_ingestion_router)
api_app = FastAPI(
    title="MultiAgentX API",
    description="API for the MultiAgentX application",
    version="1.0.0",
)

if _settings.middleware.security_headers_enabled:
    api_app.add_middleware(SecurityHeadersMiddleware)

if _settings.middleware.rate_limit_enabled:
    api_app.add_middleware(
        RateLimitMiddleware,
        max_requests=_settings.middleware.rate_limit_requests,
        window_seconds=_settings.middleware.rate_limit_window_seconds,
        excluded_paths=_settings.middleware.rate_limit_excluded_paths,
        trust_x_forwarded_for=_settings.middleware.rate_limit_trust_x_forwarded_for,
    )

if _settings.middleware.request_logging_enabled:
    api_app.add_middleware(RequestLoggingMiddleware)

api_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_app.add_exception_handler(BusinessBaseException, exception_handler)
api_app.add_exception_handler(Exception, global_exception_handler)
api_app.include_router(main_router)


@api_app.on_event("startup")
async def configure_socketio_loop() -> None:
    socketio_manager.set_event_loop(asyncio.get_running_loop())


socket_app = socketio_manager.create_asgi_app(api_app)
app = socket_app

if __name__ == "__main__":
    uvicorn.run(
        socket_app,
        host="0.0.0.0",
        port=8000,
        log_level=_settings.logging.log_level.lower(),
    )
