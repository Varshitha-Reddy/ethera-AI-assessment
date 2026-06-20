"""Per-client and global fixed-window throttling with a Redis fast path."""
import asyncio
import time
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .cache import cache_manager
from .config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._counts = defaultdict(int)
        self._lock = asyncio.Lock()

    async def _increment(self, key: str, ttl: int) -> int:
        client = cache_manager.redis_client if cache_manager.enabled else None
        if client:
            async with client.pipeline(transaction=True) as pipe:
                pipe.incr(key)
                pipe.expire(key, ttl, nx=True)
                count, _ = await pipe.execute()
                return int(count)
        async with self._lock:
            self._counts[key] += 1
            # Bound fallback memory to the current and previous minute.
            if len(self._counts) > 10_000:
                current_window = str(int(time.time() // 60))
                self._counts = defaultdict(int, {k: v for k, v in self._counts.items() if current_window in k})
            return self._counts[key]

    async def dispatch(self, request: Request, call_next):
        if not settings.rate_limit_enabled or request.url.path in {"/health", "/ready", "/metrics"}:
            return await call_next(request)
        window = int(time.time() // 60)
        forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        client_id = request.headers.get("x-client-id") or forwarded or (request.client.host if request.client else "unknown")
        global_count = await self._increment(f"ratelimit:global:{window}", 61)
        client_count = await self._increment(f"ratelimit:client:{client_id}:{window}", 61)
        if global_count > settings.global_requests_per_minute or client_count > settings.requests_per_minute:
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded", "detail": None},
                headers={"Retry-After": str(60 - int(time.time()) % 60)},
            )
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(settings.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(max(0, settings.requests_per_minute - client_count))
        return response
