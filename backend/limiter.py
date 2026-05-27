"""
limiter.py — Shared slowapi Limiter instance for NexusSwarm API routes
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# General public API default: 60 requests/minute/IP.
# Individual expensive routes can apply stricter decorators.
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
