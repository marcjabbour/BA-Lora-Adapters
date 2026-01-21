"""
LLM Client Abstraction for Step 2 Tagging

Supports: OpenAI, Anthropic, Local (vLLM/Ollama)
"""

from abc import ABC, abstractmethod
from typing import Optional


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> str:
        """Generate completion from LLM."""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return provider/model name for logging."""
        pass


def create_llm_client(
    provider: str,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
) -> LLMClient:
    """
    Factory function to create LLM clients.

    Args:
        provider: One of 'openai', 'anthropic', 'local'
        model: Model name (uses default if None)
        base_url: Base URL for local provider

    Returns:
        Configured LLMClient instance
    """
    # TODO: Implement provider-specific clients
    raise NotImplementedError("LLM client implementation pending")
