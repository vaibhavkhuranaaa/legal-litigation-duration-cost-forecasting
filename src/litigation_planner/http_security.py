"""Small ASGI admission and audit boundary for the public local API."""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import uuid4

ASGIApp = Callable[
    [dict[str, Any], Callable[..., Awaitable[Any]], Callable[..., Awaitable[Any]]], Awaitable[None]
]


class RequestTooLarge(RuntimeError):
    pass


class AdmissionControlMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        max_body_bytes: int = 64 * 1024,
        requests_per_window: int = 120,
        window_seconds: int = 60,
    ) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    async def _response(
        self,
        send: Callable[..., Awaitable[Any]],
        status: int,
        detail: str,
        request_id: str,
    ) -> None:
        body = json.dumps({"detail": detail, "request_id": request_id}).encode()
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                    (b"x-request-id", request_id.encode()),
                    (b"x-content-type-options", b"nosniff"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})

    @staticmethod
    def _audit(scope: dict[str, Any], request_id: str, status: int, started: float) -> None:
        logging.getLogger("litigation_planner.audit").info(
            json.dumps(
                {
                    "event": "http_request",
                    "request_id": request_id,
                    "method": scope.get("method"),
                    "path": scope.get("path"),
                    "status": status,
                    "duration_ms": round((time.monotonic() - started) * 1000, 3),
                },
                separators=(",", ":"),
            )
        )

    def _admit(self, client: str, now: float) -> bool:
        with self._lock:
            requests = self._requests[client]
            cutoff = now - self.window_seconds
            while requests and requests[0] <= cutoff:
                requests.popleft()
            if len(requests) >= self.requests_per_window:
                return False
            requests.append(now)
            return True

    async def __call__(self, scope: dict[str, Any], receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = uuid4().hex
        started = time.monotonic()
        client = (scope.get("client") or ("unknown", 0))[0]
        if not self._admit(client, started):
            await self._response(send, 429, "request rate limit exceeded", request_id)
            self._audit(scope, request_id, 429, started)
            return
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        content_length = headers.get(b"content-length")
        if content_length:
            try:
                declared = int(content_length)
            except ValueError:
                await self._response(send, 400, "invalid content length", request_id)
                self._audit(scope, request_id, 400, started)
                return
            if declared > self.max_body_bytes:
                await self._response(send, 413, "request body exceeds limit", request_id)
                self._audit(scope, request_id, 413, started)
                return

        received = 0
        status = 500

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_body_bytes:
                    raise RequestTooLarge
            return message

        async def secured_send(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                response_headers = list(message.get("headers", []))
                response_headers.extend(
                    [
                        (b"x-request-id", request_id.encode()),
                        (b"x-content-type-options", b"nosniff"),
                        (b"referrer-policy", b"no-referrer"),
                        (b"x-frame-options", b"DENY"),
                        (
                            b"content-security-policy",
                            (
                                b"default-src 'self'; script-src 'self'; style-src 'self'; "
                                b"connect-src 'self'; img-src 'self' data:; object-src 'none'; "
                                b"base-uri 'none'; frame-ancestors 'none'"
                            ),
                        ),
                    ]
                )
                message = {**message, "headers": response_headers}
            await send(message)

        try:
            await self.app(scope, limited_receive, secured_send)
        except RequestTooLarge:
            await self._response(send, 413, "request body exceeds limit", request_id)
            status = 413
        finally:
            self._audit(scope, request_id, status, started)
