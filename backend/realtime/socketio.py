from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import parse_qs

import socketio
from loguru import logger

from backend.utils.authentic import verify_access_token


class SocketIOManager:
    def __init__(self) -> None:
        self.sio = socketio.AsyncServer(
            async_mode="asgi",
            cors_allowed_origins="*",
            logger=False,
            engineio_logger=False,
        )
        self._loop: asyncio.AbstractEventLoop | None = None
        self._register_handlers()

    @staticmethod
    def _room_for_user(user_id: int) -> str:
        return f"user:{user_id}"

    @staticmethod
    def _normalize_token(raw_token: str | None) -> str | None:
        if not raw_token:
            return None
        token = raw_token.strip()
        if token.lower().startswith("bearer "):
            return token.split(" ", 1)[1].strip()
        return token

    def _extract_token(self, auth: Any, environ: dict[str, Any]) -> str | None:
        if isinstance(auth, dict):
            for key in (
                "token",
                "Token",
                "accessToken",
                "access_token",
                "authorization",
                "Authorization",
            ):
                token = self._normalize_token(auth.get(key))
                if token:
                    return token

        scope = environ.get("asgi.scope") or {}

        query_string = scope.get("query_string", b"")
        if isinstance(query_string, bytes):
            parsed_query = parse_qs(query_string.decode("utf-8"))
            for key in ("token", "access_token"):
                values = parsed_query.get(key)
                if values:
                    token = self._normalize_token(values[0])
                    if token:
                        return token

        raw_headers = scope.get("headers", [])
        headers: dict[str, str] = {}
        for key, value in raw_headers:
            try:
                headers[key.decode("latin-1").lower()] = value.decode("latin-1")
            except Exception:
                continue

        for key in ("token", "authorization"):
            token = self._normalize_token(headers.get(key))
            if token:
                return token

        return None

    def _register_handlers(self) -> None:
        @self.sio.event
        async def connect(sid: str, environ: dict[str, Any], auth: Any) -> bool:
            self._loop = asyncio.get_running_loop()
            token = self._extract_token(auth, environ)
            if not token:
                logger.warning("Socket connection rejected sid={} due to missing token", sid)
                return False

            try:
                is_valid, payload = verify_access_token(token)
            except Exception as exc:
                logger.warning(
                    "Socket connection rejected sid={} due to auth error: {}",
                    sid,
                    exc,
                )
                return False

            if not is_valid or not payload:
                logger.warning("Socket connection rejected sid={} due to invalid token", sid)
                return False

            user_id = payload.get("user_id")
            if user_id is None:
                logger.warning("Socket connection rejected sid={} due to missing user_id", sid)
                return False

            user_id = int(user_id)
            await self.sio.save_session(sid, {"user_id": user_id})
            await self.sio.enter_room(sid, self._room_for_user(user_id))
            logger.debug("Socket client connected sid={} user_id={}", sid, user_id)
            return True

        @self.sio.event
        async def disconnect(sid: str) -> None:
            logger.debug("Socket client disconnected sid={}", sid)

        @self.sio.event
        async def ingestion_ping(sid: str) -> dict[str, bool]:
            return {"ok": True}

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def _resolve_loop(self) -> asyncio.AbstractEventLoop | None:
        if self._loop and not self._loop.is_closed() and self._loop.is_running():
            return self._loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return None
        self._loop = loop
        return loop

    def create_asgi_app(self, fastapi_app: Any):
        return socketio.ASGIApp(self.sio, other_asgi_app=fastapi_app)

    async def emit_ingestion_status(self, *, user_id: int, payload: dict[str, Any]) -> None:
        await self.sio.emit(
            "ingestion_status",
            payload,
            room=self._room_for_user(user_id),
        )

    async def emit_sandbox_status(self, *, user_id: int, payload: dict[str, Any]) -> None:
        await self.sio.emit(
            "sandbox_status",
            payload,
            room=self._room_for_user(user_id),
        )

    async def emit_global_sandbox_status(self, *, payload: dict[str, Any]) -> None:
        await self.sio.emit("sandbox_status", payload)

    def emit_ingestion_status_sync(self, *, user_id: int, payload: dict[str, Any]) -> None:
        loop = self._resolve_loop()
        if loop:
            future = asyncio.run_coroutine_threadsafe(
                self.emit_ingestion_status(user_id=user_id, payload=payload),
                loop,
            )

            def _on_done(task_future):
                try:
                    task_future.result()
                except Exception as exc:
                    logger.warning(
                        "Failed to emit ingestion socket event for user_id={} file_id={}: {}",
                        user_id,
                        payload.get("file_id"),
                        exc,
                    )

            future.add_done_callback(_on_done)
            return

        try:
            asyncio.run(self.emit_ingestion_status(user_id=user_id, payload=payload))
        except Exception as exc:
            logger.warning(
                "Unable to emit ingestion socket event without running loop user_id={} file_id={}: {}",
                user_id,
                payload.get("file_id"),
                exc,
            )

    def emit_sandbox_status_sync(self, *, user_id: int, payload: dict[str, Any]) -> None:
        loop = self._resolve_loop()
        if loop:
            future = asyncio.run_coroutine_threadsafe(
                self.emit_sandbox_status(user_id=user_id, payload=payload),
                loop,
            )

            def _on_done(task_future):
                try:
                    task_future.result()
                except Exception as exc:
                    logger.warning(
                        "Failed to emit sandbox socket event for user_id={} sandbox_id={}: {}",
                        user_id,
                        payload.get("id"),
                        exc,
                    )

            future.add_done_callback(_on_done)
            return

        try:
            asyncio.run(self.emit_sandbox_status(user_id=user_id, payload=payload))
        except Exception as exc:
            logger.warning(
                "Unable to emit sandbox socket event without running loop user_id={} sandbox_id={}: {}",
                user_id,
                payload.get("id"),
                exc,
            )

    def emit_global_sandbox_status_sync(self, *, payload: dict[str, Any]) -> None:
        loop = self._resolve_loop()
        if loop:
            future = asyncio.run_coroutine_threadsafe(
                self.emit_global_sandbox_status(payload=payload),
                loop,
            )

            def _on_done(task_future):
                try:
                    task_future.result()
                except Exception as exc:
                    logger.warning(
                        "Failed to emit global sandbox socket event for sandbox_id={}: {}",
                        payload.get("id"),
                        exc,
                    )

            future.add_done_callback(_on_done)
            return

        try:
            asyncio.run(self.emit_global_sandbox_status(payload=payload))
        except Exception as exc:
            logger.warning(
                "Unable to emit global sandbox socket event without running loop sandbox_id={}: {}",
                payload.get("id"),
                exc,
            )


socketio_manager = SocketIOManager()
