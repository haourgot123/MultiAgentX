from __future__ import annotations

import asyncio
import math
import time
from collections import deque
from dataclasses import dataclass
from uuid import uuid4

from fastapi import Request, status
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from backend.config.settings import _settings

try:
    import redis.asyncio as redis_asyncio
except Exception:  # pragma: no cover - optional import safeguard
    redis_asyncio = None


@dataclass
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int
    remaining: int


class _InMemorySlidingWindowLimiter:
    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max(1, max_requests)
        self.window_seconds = max(1, window_seconds)
        self._buckets: dict[str, deque[float]] = {}
        self._lock = asyncio.Lock()

    async def allow(self, key: str) -> RateLimitDecision:
        now = time.monotonic()
        expire_before = now - self.window_seconds

        async with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = deque()
                self._buckets[key] = bucket

            while bucket and bucket[0] <= expire_before:
                bucket.popleft()

            if len(bucket) >= self.max_requests:
                oldest = bucket[0]
                retry_after = max(1, int(math.ceil((oldest + self.window_seconds) - now)))
                return RateLimitDecision(
                    allowed=False,
                    retry_after_seconds=retry_after,
                    remaining=0,
                )

            bucket.append(now)
            remaining = max(0, self.max_requests - len(bucket))
            return RateLimitDecision(
                allowed=True,
                retry_after_seconds=0,
                remaining=remaining,
            )


class _RedisSlidingWindowLimiter:
    _LUA_SCRIPT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window_ms = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]
local ttl_seconds = tonumber(ARGV[5])

redis.call('ZREMRANGEBYSCORE', key, '-inf', now - window_ms)
local count = redis.call('ZCARD', key)

if count < limit then
  redis.call('ZADD', key, now, member)
  redis.call('EXPIRE', key, ttl_seconds)
  return {1, limit - (count + 1), 0}
end

local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
local retry_after_ms = window_ms
if oldest[2] ~= nil then
  retry_after_ms = window_ms - (now - tonumber(oldest[2]))
  if retry_after_ms < 0 then
    retry_after_ms = 0
  end
end

return {0, 0, retry_after_ms}
"""

    def __init__(self, *, redis_url: str, max_requests: int, window_seconds: int) -> None:
        self.redis_url = redis_url
        self.max_requests = max(1, max_requests)
        self.window_seconds = max(1, window_seconds)
        self._client = None
        self._client_lock = asyncio.Lock()

    async def _get_client(self):
        if self._client is not None:
            return self._client

        async with self._client_lock:
            if self._client is not None:
                return self._client
            if redis_asyncio is None:
                raise RuntimeError("redis package is not installed")

            client = redis_asyncio.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            await client.ping()
            self._client = client
            return self._client

    async def allow(self, key: str) -> RateLimitDecision:
        client = await self._get_client()
        now_ms = int(time.time() * 1000)
        window_ms = self.window_seconds * 1000
        member = f"{now_ms}:{uuid4().hex}"
        ttl_seconds = self.window_seconds + 5

        result = await client.eval(  # noqa: S608 (constant script string)
            self._LUA_SCRIPT,
            1,
            key,
            now_ms,
            window_ms,
            self.max_requests,
            member,
            ttl_seconds,
        )
        if not isinstance(result, (list, tuple)) or len(result) < 3:
            raise RuntimeError(f"Unexpected Redis limiter response: {result}")

        allowed = bool(int(result[0]))
        remaining = max(0, int(result[1]))
        retry_after_ms = max(0, int(result[2]))
        retry_after_seconds = (
            max(1, int(math.ceil(retry_after_ms / 1000))) if not allowed else 0
        )
        return RateLimitDecision(
            allowed=allowed,
            retry_after_seconds=retry_after_seconds,
            remaining=remaining,
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        max_requests: int = 120,
        window_seconds: int = 60,
        excluded_paths: list[str] | None = None,
        trust_x_forwarded_for: bool = True,
    ) -> None:
        super().__init__(app)
        self.max_requests = max(1, max_requests)
        self.window_seconds = max(1, window_seconds)
        self.excluded_paths = tuple(excluded_paths or [])
        self.trust_x_forwarded_for = trust_x_forwarded_for
        redis_url = _settings.redis.url
        self._redis_limiter = (
            _RedisSlidingWindowLimiter(
                redis_url=redis_url,
                max_requests=self.max_requests,
                window_seconds=self.window_seconds,
            )
            if redis_url
            else None
        )
        self._fallback_limiter = _InMemorySlidingWindowLimiter(
            max_requests=self.max_requests,
            window_seconds=self.window_seconds,
        )
        self._redis_warning_logged = False

    def _is_excluded(self, path: str) -> bool:
        return any(path.startswith(prefix) for prefix in self.excluded_paths)

    def _client_key(self, request: Request) -> str:
        client_ip = "-"
        if self.trust_x_forwarded_for:
            forwarded_for = request.headers.get("X-Forwarded-For", "")
            if forwarded_for:
                client_ip = forwarded_for.split(",")[0].strip() or "-"
        if client_ip == "-" and request.client:
            client_ip = request.client.host or "-"

        return f"ratelimit:ip:{client_ip}"

    async def _allow_request(self, key: str) -> RateLimitDecision:
        if self._redis_limiter is None:
            return await self._fallback_limiter.allow(key)

        try:
            return await self._redis_limiter.allow(key)
        except Exception as exc:
            if not self._redis_warning_logged:
                logger.warning(
                    f"[RateLimit][request_id=-][user_id=-] "
                    f"Redis rate limiter unavailable, falling back to in-memory limiter: {exc}"
                )
                self._redis_warning_logged = True
            return await self._fallback_limiter.allow(key)

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if request.method.upper() == "OPTIONS" or self._is_excluded(path):
            return await call_next(request)

        decision = await self._allow_request(self._client_key(request))

        if not decision.allowed:
            request_id = getattr(request.state, "request_id", "-")
            response_headers = {
                "Retry-After": str(decision.retry_after_seconds),
                "X-RateLimit-Limit": str(self.max_requests),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Window-Seconds": str(self.window_seconds),
            }
            if request_id != "-":
                response_headers["X-Request-ID"] = request_id
            logger.warning(
                f"[RateLimit][request_id={request_id}][user_id=-] "
                f"Rate limit exceeded method={request.method} path={path} "
                f"retry_after={decision.retry_after_seconds}s"
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"message": "Too many requests. Please try again later."},
                headers=response_headers,
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(decision.remaining)
        response.headers["X-RateLimit-Window-Seconds"] = str(self.window_seconds)
        return response
