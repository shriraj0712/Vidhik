
"""
Vidhik Platform - Security Headers Middleware
==============================================
Applies security headers to outgoing responses while allowing
FastAPI documentation assets on documentation routes only.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inject standard security headers into HTTP responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        is_docs = request.url.path in {"/docs", "/redoc"}

        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' "
            "https://challenges.cloudflare.com "
            "https://accounts.google.com"
        )

        if is_docs:
            csp += " https://cdn.jsdelivr.net"

        csp += (
            "; style-src 'self' 'unsafe-inline' "
            "https://fonts.googleapis.com"
        )

        if is_docs:
            csp += " https://cdn.jsdelivr.net"

        csp += (
            "; font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: https:; "
            "connect-src 'self' "
            "http://localhost:* "
            "http://127.0.0.1:* "
            "https://challenges.cloudflare.com "
            "https://accounts.google.com; "
            "frame-src 'self' "
            "https://challenges.cloudflare.com "
            "https://accounts.google.com; "
            "frame-ancestors 'self'; "
            "object-src 'none'; "
            "base-uri 'self';"
        )

        response.headers["Content-Security-Policy"] = csp
        return response
