"""
PROMEOS — Request Context Middleware (ASGI)
Genere un request_id, mesure le temps, log en JSON, ajoute headers X-Request-Id + X-Response-Time.
"""
import time
import uuid
import logging

logger = logging.getLogger("promeos.request")


class RequestContextMiddleware:
    """ASGI middleware: request_id + timing + JSON logging."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Read or generate request_id
        request_id = None
        for h_name, h_val in scope.get("headers", []):
            if h_name == b"x-request-id":
                request_id = h_val.decode()
                break
        if not request_id:
            request_id = uuid.uuid4().hex[:12]

        start = time.perf_counter()
        status_code = 500  # default if crash

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                duration_ms = round((time.perf_counter() - start) * 1000, 1)
                headers.append((b"x-response-time", f"{duration_ms}ms".encode()))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_wrapper)

        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        method = scope.get("method", "?")
        path = scope.get("path", "?")
        logger.info(
            "request",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "status": status_code,
                "duration_ms": duration_ms,
            },
        )
