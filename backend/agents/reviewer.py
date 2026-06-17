"""
reviewer.py — Reviewer Agent Implementation
Responsible for code review, quality checks, style checks, and security analysis.
"""

import logging
from agents.llm_factory import call_agent_llm

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Reviewer Agent for NexusSwarm.
Your role is to perform rigorous code reviews of pull requests and generated code files.
Examine code for logic bugs, security vulnerabilities (specifically OWASP Top 10, SQL injection, hardcoded secrets), performance concerns, and readability.
"""

class ReviewerAgent:
    def __init__(self):
        self.name = "ReviewerAgent"

    async def review_code(self, code_to_review: str, requirements: str) -> str:
        """
        Review code against specifications and security guidelines.
        """
        logger.info(f"[{self.name}] Reviewing code...")
        prompt = f"""
Perform a code review on the following implementation.

Task Requirements:
{requirements}

Code to Review:
---
{code_to_review}
---

Your review must identify:
1. Architectural alignment (does this implement the specs?)
2. Code quality & style (readability, design patterns, idiomatic usage)
3. Security issues (input validation, rate limiting, secrets exposure, injection risks)
4. Performance bottlenecks
5. Recommendations and required changes

Provide a clear assessment: APPROVED or REQUEST_CHANGES.
"""
        return await call_agent_llm(
            agent_name=self.name,
            prompt=prompt,
            system=SYSTEM_PROMPT,
            max_tokens=2048
        )
