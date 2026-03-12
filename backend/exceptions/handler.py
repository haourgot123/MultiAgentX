from fastapi import status  # noqa
from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger

from backend.exceptions.model import BusinessBaseException
from backend.utils.constants import Message


async def exception_handler(request: Request, exc: BusinessBaseException):
    logger.bind(
        service="exception-handler",
        request_id=getattr(request.state, "request_id", "-"),
        user_id=getattr(request.state, "user_id", "-"),
        file_id="-",
        conversation_id="-",
    ).warning("Business exception raised status={} message={}", exc.status_code, exc.message)
    return JSONResponse(status_code=exc.status_code, content={"message": exc.message})


async def global_exception_handler(request: Request, exc: Exception):
    logger.bind(
        service="exception-handler",
        request_id=getattr(request.state, "request_id", "-"),
        user_id=getattr(request.state, "user_id", "-"),
        file_id="-",
        conversation_id="-",
    ).exception("Unhandled exception: {}", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"message": Message.MESSAGE_INTERNAL_SERVER_ERROR},
    )
