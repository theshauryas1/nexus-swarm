"""
llm_guardrails.py — LLM Input and Output Guardrails
Enforces prompt injection blocking, PII/Secret redaction, and hallucination validation.
"""

import re
import logging
from typing import Tuple, List, Dict
from pydantic import BaseModel
from memory.import_validator import validate_generated_imports

logger = logging.getLogger(__name__)

# PII and Secret patterns
API_KEY_PATTERN = re.compile(r"nvapi-[A-Za-z0-9-_]{76}|sk-[A-Za-z0-9-_]{48}", re.IGNORECASE)
DB_URL_PATTERN = re.compile(r"postgresql\+asyncpg://[^\s@]+:[^\s@]+@[^\s@]+/[^\s?]+", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

# Advanced Prompt Injection / Adversarial patterns
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"act\s+as\s+(?:DAN|jailbreak|evil|unrestricted|godmode)", re.IGNORECASE),
    re.compile(r"<\|?(system|im_start|im_end)\|?>", re.IGNORECASE),
    re.compile(r"\[INST\]|\[/INST\]|<<SYS>>|<</SYS>>", re.IGNORECASE),
    re.compile(r"print\s+your\s+(system\s+)?prompt", re.IGNORECASE),
    re.compile(r"reveal\s+your\s+(system\s+)?instructions?", re.IGNORECASE),
    re.compile(r"bypass\s+security|disable\s+safety|override\s+your\s+instructions", re.IGNORECASE),
]


class GuardrailResult(BaseModel):
    is_safe: bool
    reason: str
    content: str


def check_and_sanitize_input(prompt: str) -> GuardrailResult:
    """
    Scans incoming prompt for prompt injection and sensitive keys/credentials.
    Blocks if severe prompt injection is detected.
    Redacts sensitive details (PII, credentials) to prevent data leakage.
    """
    if not prompt:
        return GuardrailResult(is_safe=True, reason="Empty prompt", content=prompt)

    # 1. Check for prompt injection
    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern.search(prompt):
            logger.warning(f"🚨 LLM Input Guardrail triggered: prompt injection pattern detected ({pattern.pattern})")
            return GuardrailResult(
                is_safe=False,
                reason=f"Security alert: Prompt injection pattern detected.",
                content=prompt
            )

    # 2. Redact sensitive info (secrets, DB URLs, email)
    sanitized = prompt
    if API_KEY_PATTERN.search(sanitized):
        logger.info("🔒 Redacting API Key from LLM input")
        sanitized = API_KEY_PATTERN.sub("[REDACTED_API_KEY]", sanitized)
        
    if DB_URL_PATTERN.search(sanitized):
        logger.info("🔒 Redacting Database URL from LLM input")
        sanitized = DB_URL_PATTERN.sub("[REDACTED_DB_CONNECTION]", sanitized)

    if EMAIL_PATTERN.search(sanitized):
        logger.info("🔒 Redacting Email address from LLM input")
        sanitized = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", sanitized)

    return GuardrailResult(is_safe=True, reason="Prompt passed guardrails", content=sanitized)


def check_and_sanitize_output(output: str, filename: str = "", workspace_dir: str = "") -> GuardrailResult:
    """
    Scans LLM output for sensitive keys/credentials leakage.
    Also validates generated code for import hallucinations.
    """
    if not output:
        return GuardrailResult(is_safe=True, reason="Empty output", content=output)

    # 1. Redact secrets leaked in output
    sanitized = output
    if API_KEY_PATTERN.search(sanitized):
        logger.warning("🚨 LLM Output Guardrail triggered: leaked API Key redacted")
        sanitized = API_KEY_PATTERN.sub("[REDACTED_API_KEY]", sanitized)

    if DB_URL_PATTERN.search(sanitized):
        logger.warning("🚨 LLM Output Guardrail triggered: leaked Database URL redacted")
        sanitized = DB_URL_PATTERN.sub("[REDACTED_DB_CONNECTION]", sanitized)

    # 2. If generating python code, validate imports statically
    is_python_code = False
    if filename.endswith(".py") or "```python" in output or "```py" in output:
        is_python_code = True

    if is_python_code:
        # Extract code block content if it exists
        code_to_check = output
        fence_match = re.search(r"```(?:python|py)?\s*\n(.*?)```", output, re.DOTALL | re.IGNORECASE)
        if fence_match:
            code_to_check = fence_match.group(1)

        findings = validate_generated_imports(code_to_check, workspace_dir=workspace_dir or None)
        hallucinated = [f for f in findings if f.get("type") == "hallucinated_api" or f.get("type") == "missing_import"]
        if hallucinated:
            reasons = "; ".join([f["reason"] for f in hallucinated])
            logger.warning(f"⚠️ Hallucination detected in generated code: {reasons}")
            # We don't block the output completely, but we add a warning/audit note
            return GuardrailResult(
                is_safe=True,
                reason=f"Hallucination Warning: {reasons}",
                content=sanitized
            )

    return GuardrailResult(is_safe=True, reason="Output passed guardrails", content=sanitized)
