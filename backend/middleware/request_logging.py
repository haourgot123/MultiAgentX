from __future__ import annotations

from time import perf_counter
from uuid import uuid4

from fastapi import Request
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log inbound/outbound HTTP requests with request id and latency."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id

        method = request.method
        path = request.url.path
        start = perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (perf_counter() - start) * 1000
            user_id = getattr(request.state, "user_id", "-")
            logger.exception(
                f"[Middleware][request_id={request_id}][user_id={user_id}] "
                f"HTTP request failed method={method} path={path} duration_ms={elapsed_ms:.2f}"
            )
            raise

        elapsed_ms = (perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"
        user_id = getattr(request.state, "user_id", "-")
        logger.info(
            f"[Middleware][request_id={request_id}][user_id={user_id}] "
            f"HTTP request completed method={method} path={path} duration_ms={elapsed_ms:.2f}"
        )
        return response
