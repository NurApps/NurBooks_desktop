"""In-memory rate limiter (скользящее окно) для NurBooks API."""
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# Не даём словарю расти бесконечно (защита от IP-флуда/утечки памяти).
MAX_TRACKED_CLIENTS = 20_000


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Ограничивает число запросов с одного IP за окно времени.

    Подходит для одного инстанса (Render free tier). Для нескольких инстансов
    нужен общий стор (Redis). ``trust_forwarded_for`` включайте только если
    приложение стоит за доверенным прокси, который сам выставляет X-Forwarded-For.
    """

    def __init__(
        self,
        app,
        max_requests: int = 120,
        window_seconds: int = 60,
        exempt_paths=None,
        trust_forwarded_for: bool = False,
        path_limits: dict | None = None,
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.exempt_paths = set(exempt_paths or [])
        self.trust_forwarded_for = trust_forwarded_for
        self.path_limits = path_limits or {}
        self._hits = defaultdict(deque)
        self._requests = 0

    def _client_key(self, request) -> str:
        if self.trust_forwarded_for:
            forwarded = request.headers.get("X-Forwarded-For", "")
            if forwarded:
                # Первый адрес — клиент; ограничиваем число хопов, чтобы не раздувать строку.
                parts = [p.strip() for p in forwarded.split(",") if p.strip()]
                if parts:
                    return parts[0][:64]
        return request.client.host if request.client else "unknown"

    def _bucket_for(self, path: str) -> str:
        best_prefix = ""
        for prefix in self.path_limits:
            if path.startswith(prefix) and len(prefix) > len(best_prefix):
                best_prefix = prefix
        return best_prefix

    def _limit_for(self, path: str) -> int:
        bucket = self._bucket_for(path)
        if bucket:
            return int(self.path_limits[bucket])
        return self.max_requests

    def _cleanup(self, now: float):
        self._requests += 1
        if self._requests % 1000 != 0:
            return
        cutoff = now - self.window_seconds
        for key in list(self._hits.keys()):
            window = self._hits[key]
            while window and window[0] < cutoff:
                window.popleft()
            if not window:
                self._hits.pop(key, None)
        # Аварийная эвикция самых старых ключей при переполнении.
        while len(self._hits) > MAX_TRACKED_CLIENTS:
            self._hits.pop(next(iter(self._hits)), None)

    async def dispatch(self, request, call_next):
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        client = self._client_key(request)
        bucket = self._bucket_for(request.url.path)
        key = f"{client}|{bucket}"
        now = time.time()
        self._cleanup(now)
        window = self._hits[key]

        while window and window[0] < now - self.window_seconds:
            window.popleft()

        limit = self._limit_for(request.url.path)
        if len(window) >= limit:
            retry_after = max(1, int(self.window_seconds - (now - window[0])))
            return JSONResponse(
                {"detail": "Too many requests"},
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )

        window.append(now)
        return await call_next(request)
