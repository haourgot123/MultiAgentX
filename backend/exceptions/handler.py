from loguru import logger
from fastapi import Request
from fastapi.responses import JSONResponse
from backend.exceptions.model import BusinessBaseException
from fastapi import status  # noqa
from backend.utils.constants import Message


async def exception_handler(request: Request, exc: BusinessBaseException):
    logger.error(f"Exception: {exc.message}")
    return JSONResponse(status_code=exc.status_code, content={"message": exc.message})

async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Exception: {exc}")
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"message": Message.INTERNAL_SERVER_ERROR})