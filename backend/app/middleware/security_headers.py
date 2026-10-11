"""
Vidhik Platform - Security Headers Middleware
==============================================
Applies OWASP-recommended HTTP security headers to all outgoing responses,
protecting against MIME sniffing, clickjacking, cross-site scripting (XSS),
and insecure referrer leakage while preserving full compatibility with the
single-page static application.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Injects standard security headers onto every HTTP response.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # 1. Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # 2. Prevent clickjacking (SAMEORIGIN allows embedded SPA if needed)
        response.headers["X-Frame-Options"] = "SAMEORIGIN"

        # 3. Referrer leakage prevention
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # 4. Cross-site scripting legacy filter
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # 5. Content Security Policy compatible with static UI, fonts, and inline styles
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' "
            "https://challenges.cloudflare.com "
            "https://accounts.google.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
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
