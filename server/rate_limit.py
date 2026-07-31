"""Простой in-memory rate limiter (скользящее окно) для NurBooks API."""
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Ограничивает число запросов с одного IP за окно времени.

    Подходит для одного инстанса (Render free tier). Exempt paths (например,
    /health) не ограничиваются, чтобы не срывать мониторинг.
    """

    def __init__(self, app, max_requests: int = 120, window_seconds: int = 60, exempt_paths=None):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.exempt_paths = set(exempt_paths or [])
        self._hits = defaultdict(deque)

    async def dispatch(self, request, call_next):
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        client = request.client.host if request.client else "unknown"
        now = time.time()
        window = self._hits[client]

        while window and window[0] < now - self.window_seconds:
            window.popleft()

        if len(window) >= self.max_requests:
            return JSONResponse({"detail": "Too many requests"}, status_code=429)

        window.append(now)
        return await call_next(request)
