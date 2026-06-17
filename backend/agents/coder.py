"""
coder.py — Coder Agent Implementation
Responsible for code generation, refactoring, and bug fixing.
"""

import logging
from typing import Optional
from agents.llm_factory import call_agent_llm

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Coder Agent for NexusSwarm.
Your role is to write clean, maintainable, and highly secure code that implements the requested functionality or designs.
Ensure your code strictly adheres to security rules (parameterized queries, input validation, proper error handling, no secrets).
"""

class CoderAgent:
    def __init__(self):
        self.name = "CoderAgent"

    async def generate_code(self, task_title: str, requirements: str, design_spec: str, existing_code: Optional[str] = None) -> str:
        """
        Generate implementation code based on requirements and design specs.
        """
        logger.info(f"[{self.name}] Generating code for task: '{task_title}'")
        prompt = f"""
Write code to satisfy the requirements and match the architectural design spec below.

Task Title: {task_title}
Requirements: {requirements}

Design Specification:
{design_spec}
"""
        if existing_code:
            prompt += f"\nExisting Codebase Context:\n{existing_code}\nPlease integrate or update the existing code rather than rewriting from scratch."

        prompt += "\nOutput only the raw code file. Adhere strictly to the requested language syntax."
        
        return await call_agent_llm(
            agent_name=self.name,
            prompt=prompt,
            system=SYSTEM_PROMPT,
            max_tokens=4096
        )
