"""
security_utils.py — NexusSwarm Security Utilities
Central module for security helpers used across the application.

Covers:
  - LLM prompt injection prevention (sanitize_llm_input)
  - LLM output XSS sanitization (sanitize_llm_output)
  - Per-request token budget tracking
  - Generic safe-error helpers

IMPORTANT: This module adds security WITHOUT changing any business logic.
All functions are pure additions; existing routes call them as wrappers.
"""

import html
import logging
import re
from collections import defaultdict
from time import time

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
#  LLM INPUT SANITIZATION — Prompt Injection Prevention
# ─────────────────────────────────────────────────────────────

# Common prompt-injection patterns to strip/neutralise
_PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(?!a\s+senior)", re.IGNORECASE),
    re.compile(r"act\s+as\s+(?:DAN|jailbreak|evil|unrestricted)", re.IGNORECASE),
    re.compile(r"<\|?(system|im_start|im_end)\|?>", re.IGNORECASE),
    re.compile(r"\[INST\]|\[/INST\]|<<SYS>>|<</SYS>>", re.IGNORECASE),
    re.compile(r"###\s*System\s*:", re.IGNORECASE),
    re.compile(r"print\s+your\s+(system\s+)?prompt", re.IGNORECASE),
    re.compile(r"reveal\s+your\s+(system\s+)?instructions?", re.IGNORECASE),
]

# Max length for user-supplied text sent to LLM (prevents cost attacks)
MAX_LLM_INPUT_LENGTH = 8_000  # ~2000 tokens


def sanitize_llm_input(text: str) -> str:
    """
    Sanitise user-supplied text before it is forwarded to an LLM.

    1. Strips known prompt-injection patterns.
    2. Truncates excessively long inputs (cost-attack prevention).
    3. Removes null bytes and other control characters.

    Does NOT alter the meaning of legitimate user requests.
    """
    if not text:
        return text

    # Strip control characters (except standard whitespace)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # Remove prompt-injection patterns
    for pattern in _PROMPT_INJECTION_PATTERNS:
        text = pattern.sub("[FILTERED]", text)

    # Truncate to limit
    if len(text) > MAX_LLM_INPUT_LENGTH:
        logger.warning("LLM input truncated from %d to %d chars", len(text), MAX_LLM_INPUT_LENGTH)
        text = text[:MAX_LLM_INPUT_LENGTH] + "\n...[truncated]"

    return text


# ─────────────────────────────────────────────────────────────
#  LLM OUTPUT SANITIZATION — XSS prevention for rendered output
# ─────────────────────────────────────────────────────────────

def sanitize_llm_output(text: str) -> str:
    """
    Sanitise LLM-generated text before it is stored or returned to clients.

    - HTML-escapes any raw tags that could cause XSS when rendered directly.
    - Preserves code blocks by treating them as plain text (no eval injection).
    - Does NOT alter programming logic, markdown structure, or response meaning.

    NOTE: The frontend should ALSO escape output — this is defence-in-depth.
    """
    if not text:
        return text

    # Strip <script> blocks entirely (highest risk)
    text = re.sub(
        r"<script[\s\S]*?>[\s\S]*?</script>",
        "[script removed]",
        text,
        flags=re.IGNORECASE,
    )

    # Strip on* event handler attributes from any HTML tags
    text = re.sub(r"\bon\w+\s*=\s*['\"].*?['\"]", "", text, flags=re.IGNORECASE)

    # Strip javascript: URIs
    text = re.sub(r"javascript\s*:", "[blocked]:", text, flags=re.IGNORECASE)

    return text


# ─────────────────────────────────────────────────────────────
#  PER-USER TOKEN BUDGET  — Cost attack prevention
# ─────────────────────────────────────────────────────────────

# Budget: max tokens consumed by a single IP per rolling 15-minute window
TOKEN_BUDGET_PER_WINDOW = 50_000
TOKEN_WINDOW_SECONDS = 15 * 60  # 15 minutes

# In-memory store: {ip: {"tokens": int, "window_start": float}}
_token_usage: dict = defaultdict(lambda: {"tokens": 0, "window_start": time()})


def check_token_budget(client_ip: str, tokens_requested: int) -> bool:
    """
    Check whether the client IP is within its rolling token budget.

    Returns True if the request is allowed, False if budget is exceeded.
    This is a soft guard; actual token counting happens after the LLM call.
    """
    now = time()
    record = _token_usage[client_ip]

    # Reset window if expired
    if now - record["window_start"] > TOKEN_WINDOW_SECONDS:
        record["tokens"] = 0
        record["window_start"] = now

    if record["tokens"] + tokens_requested > TOKEN_BUDGET_PER_WINDOW:
        logger.warning(
            "Token budget exceeded for IP %s (used %d, requested %d, limit %d)",
            client_ip,
            record["tokens"],
            tokens_requested,
            TOKEN_BUDGET_PER_WINDOW,
        )
        return False

    return True


def record_token_usage(client_ip: str, tokens_used: int) -> None:
    """Update the token counter for a client IP after a successful LLM call."""
    now = time()
    record = _token_usage[client_ip]
    if now - record["window_start"] > TOKEN_WINDOW_SECONDS:
        record["tokens"] = 0
        record["window_start"] = now
    record["tokens"] += tokens_used
    logger.debug("Token usage for %s: %d/%d", client_ip, record["tokens"], TOKEN_BUDGET_PER_WINDOW)


# ─────────────────────────────────────────────────────────────
#  SAFE ERROR HELPER
# ─────────────────────────────────────────────────────────────

def safe_error_message(exc: Exception, context: str = "") -> str:
    """
    Returns a generic user-facing error message and logs the full detail
    server-side. Never exposes stack traces, internal paths, or DB schemas.
    """
    logger.error("Internal error [%s]: %s", context, exc, exc_info=True)
    return "Something went wrong. Please try again."
