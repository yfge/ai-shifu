"""Base contracts and errors for ask provider adapters."""

from dataclasses import dataclass
from typing import Any, Generator, Protocol

from flask import Flask


@dataclass
class AskProviderChunk:
    content: str


class AskProviderError(Exception):
    """Base exception for ask provider invocation errors."""


class AskProviderConfigError(AskProviderError):
    """Provider configuration is missing or invalid."""


class AskProviderTimeoutError(AskProviderError):
    """Provider request timed out."""


class AskProviderAdapter(Protocol):
    provider: str

    def stream_answer(
        self,
        app: Flask,
        user_id: str,
        user_query: str,
        messages: list[dict[str, Any]],
        provider_config: dict[str, Any],
    ) -> Generator[AskProviderChunk, None, None]: ...
