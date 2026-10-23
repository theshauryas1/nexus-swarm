"""
limiter.py — Shared slowapi Limiter instance for NexusSwarm API routes
"""

from fastapi import Request
from slowapi import Limiter


def get_real_ip(request: Request) -> str:
    """Extract real client IP taking into account reverse proxies (Cloud Run / GFE)."""
    forwarded = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


# General public API default: 60 requests/minute/IP.
# Individual expensive routes apply stricter decorators (e.g. 10/min for /submit-task, 5/min for downloads).
limiter = Limiter(key_func=get_real_ip, default_limits=["60/minute"])
