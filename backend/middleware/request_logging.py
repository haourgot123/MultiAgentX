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
        client_ip = request.client.host if request.client else "-"
        start = perf_counter()

        logger.bind(
            service="http-middleware",
            request_id=request_id,
            user_id=getattr(request.state, "user_id", "-"),
        ).info("HTTP request started method={} path={} client_ip={}", method, path, client_ip)

        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (perf_counter() - start) * 1000
            logger.bind(
                service="http-middleware",
                request_id=request_id,
                user_id=getattr(request.state, "user_id", "-"),
            ).exception(
                "HTTP request failed method={} path={} duration_ms={:.2f}",
                method,
                path,
                elapsed_ms,
            )
            raise

        elapsed_ms = (perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"
        logger.bind(
            service="http-middleware",
            request_id=request_id,
            user_id=getattr(request.state, "user_id", "-"),
        ).info(
            "HTTP request completed method={} path={} status={} duration_ms={:.2f}",
            method,
            path,
            response.status_code,
            elapsed_ms,
        )
        return response
