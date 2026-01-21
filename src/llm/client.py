"""
LLM Client Abstraction for Step 2 Tagging

Supports: OpenAI, Anthropic, Local (vLLM/Ollama)
"""

import os
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


class OpenAIClient(LLMClient):
    """OpenAI API client."""

    def __init__(self, model: str = "gpt-4o", api_key: Optional[str] = None):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package required: pip install openai")

        self.model = model
        api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")
        self.client = OpenAI(api_key=api_key)

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    def get_name(self) -> str:
        return f"openai/{self.model}"


class AnthropicClient(LLMClient):
    """Anthropic API client."""

    def __init__(self, model: str = "claude-sonnet-4-20250514", api_key: Optional[str] = None):
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError("anthropic package required: pip install anthropic")

        self.model = model
        api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")
        self.client = Anthropic(api_key=api_key)

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=temperature,
        )
        # Extract text from the first TextBlock in the response
        content_block = response.content[0]
        if hasattr(content_block, "text"):
            return content_block.text  # type: ignore[union-attr]
        return ""

    def get_name(self) -> str:
        return f"anthropic/{self.model}"


class LocalClient(LLMClient):
    """Local LLM client (vLLM/Ollama via OpenAI-compatible API)."""

    def __init__(
        self,
        model: str = "meta-llama/Llama-3.1-8B-Instruct",
        base_url: str = "http://localhost:8000/v1",
    ):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package required: pip install openai")

        self.model = model
        self.base_url = base_url
        self.client = OpenAI(base_url=base_url, api_key="not-needed")

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    def get_name(self) -> str:
        return f"local/{self.model}"


def create_llm_client(
    provider: str,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> LLMClient:
    """
    Factory function to create LLM clients.

    Args:
        provider: One of 'openai', 'anthropic', 'local'
        model: Model name (uses default if None)
        base_url: Base URL for local provider
        api_key: API key (uses environment variable if None)

    Returns:
        Configured LLMClient instance
    """
    if provider == "openai":
        return OpenAIClient(
            model=model or "gpt-4o",
            api_key=api_key,
        )
    elif provider == "anthropic":
        return AnthropicClient(
            model=model or "claude-sonnet-4-20250514",
            api_key=api_key,
        )
    elif provider == "local":
        return LocalClient(
            model=model or "meta-llama/Llama-3.1-8B-Instruct",
            base_url=base_url or "http://localhost:8000/v1",
        )
    else:
        raise ValueError(f"Unknown provider: {provider}. Must be 'openai', 'anthropic', or 'local'")
