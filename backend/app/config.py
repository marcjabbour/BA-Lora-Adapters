"""Application configuration."""

import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # API settings
    api_title: str = "LoRA Training Pipeline API"
    api_version: str = "1.0.0"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # CORS settings
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Session settings
    session_cleanup_hours: int = 24
    temp_base_dir: Path = Path("/tmp")

    # Project root (2 levels up from this file)
    project_root: Path = Path(__file__).parent.parent.parent

    # Paths to pipeline scripts
    scripts_dir: Path = project_root / "scripts"

    # File upload limits
    max_upload_size_mb: int = 500

    # LLM API keys (loaded from environment)
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    class Config:
        """Pydantic settings config."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
