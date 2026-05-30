"""
NexusSwarm — Application Configuration
Dual LLM provider support: Azure OpenAI + NVIDIA NIM
"""

from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ────────────────────────────────────────────────────────
    app_env: str = "development"
    app_secret_key: str = ""
    log_level: str = "INFO"
    cors_allowed_origins: str = "http://localhost:3000,http://localhost:80,http://127.0.0.1:3000"
    cors_allowed_methods: str = "GET,POST"
    cors_allowed_headers: str = "Content-Type,Authorization"
    cors_allow_credentials: bool = False
    trusted_hosts: str = "localhost,127.0.0.1,testserver"

    # ── Agent Config ───────────────────────────────────────────────
    max_agent_retries: int = 3
    agent_timeout_seconds: int = 120
    max_concurrent_pipelines: int = 3

    # ── NVIDIA NIM ─────────────────────────────────────────────────
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nim_orchestrator_model: str = "meta/llama-3.1-70b-instruct"
    nim_manager_model: str = "meta/llama-3.1-70b-instruct"
    nim_worker_model: str = "meta/llama-3.1-8b-instruct"

    # ── Azure OpenAI ───────────────────────────────────────────────
    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_deployment_orchestrator: str = "gpt-4o"
    azure_openai_deployment_manager: str = "gpt-4o"
    azure_openai_api_version: str = "2024-08-01-preview"

    # ── LLM Routing ────────────────────────────────────────────────
    llm_provider: Literal["azure", "nvidia", "auto"] = "auto"

    # ── Infrastructure ─────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379"
    database_url: str = ""
    s3_bucket: str = ""
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""


    # ── GitHub MCP ─────────────────────────────────────────────────
    github_token: str = ""
    github_repo_owner: str = ""
    github_default_repo: str = "nexusswarm-workspace"

    # ─── Computed Properties ────────────────────────────────────────
    @property
    def azure_available(self) -> bool:
        return bool(self.azure_openai_api_key and self.azure_openai_endpoint)

    @property
    def nvidia_available(self) -> bool:
        return bool(self.nvidia_api_key)

    @property
    def resolved_provider(self) -> str:
        """Resolve the actual provider based on availability."""
        if self.llm_provider == "azure":
            if not self.azure_available:
                raise ValueError("Azure OpenAI configured but credentials missing")
            return "azure"
        if self.llm_provider == "nvidia":
            if not self.nvidia_available:
                raise ValueError("NVIDIA NIM configured but API key missing")
            return "nvidia"
        # auto mode
        if self.azure_available:
            return "azure"
        if self.nvidia_available:
            return "nvidia"
        # Graceful fallback instead of crashing
        return "mock"

    def get_llm_config(self, role: Literal["orchestrator", "manager", "worker"]) -> dict:
        """
        Returns AutoGen-compatible LLM config for a given agent role.
        Orchestrators + Managers get the powerful model.
        Workers get the fast/cheap model.
        """
        provider = self.resolved_provider

        if provider == "mock":
            return {
                "config_list": [
                    {
                        "model": "mock-model",
                        "api_key": "mock-key",
                        "base_url": "mock-url",
                    }
                ],
                "temperature": 0.0,
                "timeout": 60,
            }

        if provider == "azure":
            deployment = (
                self.azure_openai_deployment_orchestrator
                if role in ("orchestrator", "manager")
                else self.azure_openai_deployment_manager
            )
            return {
                "config_list": [
                    {
                        "model": deployment,
                        "api_key": self.azure_openai_api_key,
                        "base_url": self.azure_openai_endpoint,
                        "api_type": "azure",
                        "api_version": self.azure_openai_api_version,
                    }
                ],
                "temperature": 0.1 if role == "orchestrator" else 0.3,
                "timeout": self.agent_timeout_seconds,
            }

        # NVIDIA NIM (OpenAI-compatible endpoint)
        model = (
            self.nim_orchestrator_model
            if role == "orchestrator"
            else self.nim_manager_model
            if role == "manager"
            else self.nim_worker_model
        )
        return {
            "config_list": [
                {
                    "model": model,
                    "api_key": self.nvidia_api_key,
                    "base_url": self.nvidia_base_url,
                }
            ],
            "temperature": 0.1 if role == "orchestrator" else 0.3,
            "timeout": self.agent_timeout_seconds,
        }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
