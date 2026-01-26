"""Application configuration."""

import os
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # API settings
    api_title: str = "LoRA Training Pipeline API"
    api_version: str = "1.0.0"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # CORS settings - store as string from env, parse in validator
    cors_origins: str = Field(default="http://localhost:5173,http://localhost:5174,http://localhost:3000")

    # Session settings
    session_cleanup_hours: int = 24
    temp_base_dir: Path = Path("/tmp")

    # Project root (2 levels up from this file)
    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent)

    # File upload limits
    max_upload_size_mb: int = 500

    # LLM API keys (loaded from environment)
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def scripts_dir(self) -> Path:
        """Path to pipeline scripts directory."""
        return self.project_root / "scripts"

    def get_cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list."""
        if isinstance(self.cors_origins, str):
            return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        return self.cors_origins


# Global settings instance
settings = Settings()
