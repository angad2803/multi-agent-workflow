"""LLM Provider factory for multi-provider support."""

import os
import time
from threading import Lock
from enum import Enum
from typing import Any

from langchain_core.language_models import BaseChatModel
from src.shared.metrics import increment


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_seconds: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self.failures = 0
        self.opened_at = 0.0
        self._lock = Lock()

    def before_call(self) -> None:
        with self._lock:
            if self.failures >= self.failure_threshold:
                if time.monotonic() - self.opened_at < self.recovery_seconds:
                    increment("circuit_breaker_events")
                    raise RuntimeError("LLM circuit breaker is open")
                self.opened_at = 0.0

    def record_success(self) -> None:
        with self._lock:
            self.failures = 0
            self.opened_at = 0.0

    def record_failure(self) -> None:
        with self._lock:
            self.failures += 1
            if self.failures >= self.failure_threshold:
                self.opened_at = time.monotonic()
                increment("circuit_breaker_events")


_circuit_breaker = CircuitBreaker()


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    GROQ = "groq"


# Default models for each provider
DEFAULT_MODELS = {
    LLMProvider.OPENAI: "gpt-4o-mini",
    LLMProvider.GROQ: "openai/gpt-oss-120b",
}


def get_llm_provider() -> LLMProvider:
    """
    Get the configured LLM provider from environment.
    
    Environment variable: LLM_PROVIDER
    Default: groq
    """
    provider = os.environ.get("LLM_PROVIDER", "groq").lower()
    
    try:
        return LLMProvider(provider)
    except ValueError:
        # Default to Groq if invalid provider specified
        return LLMProvider.GROQ


def get_llm(
    temperature: float = 0.3,
    model: str | None = None,
    provider: LLMProvider | None = None,
    **kwargs: Any,
) -> BaseChatModel:
    """
    Get an LLM instance based on the configured provider.
    
    Args:
        temperature: Model temperature (0.0-1.0)
        model: Optional model name override
        provider: Optional provider override (uses env var if not specified)
        **kwargs: Additional provider-specific arguments
        
    Returns:
        A LangChain chat model instance
        
    Raises:
        ValueError: If required API key is not set
    """
    if provider is None:
        provider = get_llm_provider()
    
    if model is None:
        model = os.environ.get("LLM_MODEL") or DEFAULT_MODELS.get(provider)
    
    if provider == LLMProvider.OPENAI:
        return _get_openai_llm(model, temperature, **kwargs)
    elif provider == LLMProvider.GROQ:
        return _get_groq_llm(model, temperature, **kwargs)
    else:
        raise ValueError(f"Unsupported provider: {provider}")


def _get_openai_llm(
    model: str,
    temperature: float,
    **kwargs: Any,
) -> BaseChatModel:
    """Create an OpenAI chat model."""
    from langchain_openai import ChatOpenAI
    
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY")
    
    if not api_key:
        raise ValueError(
            "OpenAI API key not found. Set OPENAI_API_KEY or LLM_API_KEY environment variable."
        )
    
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        temperature=temperature,
        timeout=float(os.getenv("LLM_TIMEOUT_SECONDS", "30")),
        **kwargs,
    )


def _get_groq_llm(
    model: str,
    temperature: float,
    **kwargs: Any,
) -> BaseChatModel:
    """Create a Groq chat model."""
    from langchain_groq import ChatGroq
    
    api_key = os.environ.get("GROQ_API_KEY") or os.environ.get("LLM_API_KEY")
    
    if not api_key:
        raise ValueError(
            "Groq API key not found. Set GROQ_API_KEY or LLM_API_KEY environment variable."
        )
    
    return ChatGroq(
        model=model,
        api_key=api_key,
        temperature=temperature,
        timeout=float(os.getenv("LLM_TIMEOUT_SECONDS", "30")),
        **kwargs,
    )


def invoke_llm(llm: BaseChatModel, prompt: str):
    _circuit_breaker.before_call()
    try:
        response = llm.invoke(prompt)
    except Exception:
        increment("llm_failures")
        _circuit_breaker.record_failure()
        raise
    _circuit_breaker.record_success()
    return response
