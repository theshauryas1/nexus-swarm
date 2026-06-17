"""
architect.py — Architect Agent Implementation
Responsible for system design, planning, and creating technical specs.
"""

import logging
from typing import Optional
from agents.llm_factory import call_agent_llm

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Architect Agent for NexusSwarm.
Your role is to analyze user requests/issues and design complete, robust system architectures, API specifications, and database schemas.
Always prioritize clean design, separation of concerns, scalability, and adherence to security guidelines.
"""

class ArchitectAgent:
    def __init__(self):
        self.name = "ArchitectAgent"
        
    async def design_system(self, task_title: str, task_description: str, context: Optional[str] = None) -> str:
        """
        Generate system architecture and design specifications.
        """
        logger.info(f"[{self.name}] Designing system for task: '{task_title}'")
        prompt = f"""
Analyze the following request and generate a comprehensive architecture and design specification.

Title: {task_title}
Description: {task_description}
"""
        if context:
            prompt += f"\nAdditional Context:\n{context}"
            
        prompt += """
Your specification should include:
1. Architectural Overview & Design Decisions
2. Component Diagrams / Flow Diagrams
3. Database Schemas / Data Models (if applicable)
4. API / Endpoint Specifications (if applicable)
5. Security Measures & Potential Risks
"""
        return await call_agent_llm(
            agent_name=self.name,
            prompt=prompt,
            system=SYSTEM_PROMPT,
            max_tokens=4096
        )
