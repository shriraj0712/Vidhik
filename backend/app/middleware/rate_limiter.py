"""
Vidhik Platform - Authentication Rate Limiting Middleware
=========================================================
Implements an in-memory sliding-window rate limiter targeting sensitive
authentication endpoints (/api/auth/login, /api/auth/register, /api/auth/forgot-password,
/api/auth/reset-password) to prevent brute-force attacks and credential stuffing.
No Redis or external service dependency.
"""

import os
import time
from collections import defaultdict
from typing import Dict, List
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


# Default: 30 requests per minute per IP for sensitive auth routes
DEFAULT_AUTH_LIMIT = int(os.getenv("AUTH_RATE_LIMIT_PER_MINUTE", "60"))

# Sensitive endpoints subject to rate limiting
SENSITIVE_PATHS = {
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/forgot-password",
    "/api/auth/reset-password"
}


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    In-memory IP-based sliding window rate limiter.
    """

    def __init__(self, app, limit_per_minute: int = DEFAULT_AUTH_LIMIT):
        super().__init__(app)
        self.limit = limit_per_minute
        self.window_seconds = 60
        # Maps ip -> list of request timestamps
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self._last_cleanup = time.time()

    def _cleanup_stale_entries(self, now: float):
        """Removes request records older than the active window."""
        if now - self._last_cleanup < 30:
            return
        cutoff = now - self.window_seconds
        for ip in list(self.requests.keys()):
            self.requests[ip] = [ts for ts in self.requests[ip] if ts > cutoff]
            if not self.requests[ip]:
                del self.requests[ip]
        self._last_cleanup = now

    def get_client_ip(self, request: Request) -> str:
        """Extracts client IP considering standard reverse-proxy headers."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        client = request.client
        return client.host if client else "127.0.0.1"

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        method = request.method

        # Only apply rate limiting to POST requests on sensitive auth endpoints
        if method == "POST" and path in SENSITIVE_PATHS:
            ip = self.get_client_ip(request)
            now = time.time()
            self._cleanup_stale_entries(now)

            # Filter timestamps within current window
            cutoff = now - self.window_seconds
            timestamps = [ts for ts in self.requests[ip] if ts > cutoff]
            self.requests[ip] = timestamps

            if len(timestamps) >= self.limit:
                retry_after = int(self.window_seconds - (now - timestamps[0])) + 1
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Too many authentication requests. Please try again later.",
                        "retry_after_seconds": max(1, retry_after)
                    },
                    headers={"Retry-After": str(max(1, retry_after))}
                )

            self.requests[ip].append(now)

        return await call_next(request)
