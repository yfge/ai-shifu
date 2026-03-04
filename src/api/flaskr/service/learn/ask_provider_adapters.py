"""Ask provider adapters for streaming external KB answers."""

from dataclasses import dataclass
from typing import Any, Generator, Iterable, Protocol
import json

import requests
from flask import Flask

from flaskr.service.config import get_config
from flaskr.service.shifu.shifu_draft_funcs import (
    ASK_PROVIDER_DIFY,
    ASK_PROVIDER_COZE,
)


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


def _provider_timeout_seconds() -> int:
    raw = get_config("ASK_PROVIDER_TIMEOUT_SECONDS")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = 20
    return max(value, 1)


def _iter_sse_payloads(response: requests.Response) -> Iterable[str]:
    for line in response.iter_lines(decode_unicode=True):
        if not line:
            continue
        normalized = line.strip()
        if normalized.startswith("data:"):
            yield normalized[5:].strip()
        else:
            yield normalized


def _extract_text(payload: Any) -> str:
    if isinstance(payload, str):
        return payload
    if isinstance(payload, list):
        for item in payload:
            text = _extract_text(item)
            if text:
                return text
        return ""
    if not isinstance(payload, dict):
        return ""

    for key in ("answer", "content", "text", "output"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value

    nested_data = payload.get("data")
    if isinstance(nested_data, str):
        try:
            nested_data = json.loads(nested_data)
        except Exception:
            pass
    nested_text = _extract_text(nested_data)
    if nested_text:
        return nested_text

    nested_message = payload.get("message")
    nested_text = _extract_text(nested_message)
    if nested_text:
        return nested_text

    return ""


def _raise_for_provider_response(
    response: requests.Response, provider: str
) -> requests.Response:
    try:
        response.raise_for_status()
        return response
    except requests.HTTPError as exc:
        detail = ""
        try:
            detail = response.text
        except Exception:
            detail = ""
        message = f"{provider} request failed: {exc}"
        if detail:
            message += f" | {detail[:300]}"
        raise AskProviderError(message) from exc


class DifyAskProviderAdapter:
    provider = ASK_PROVIDER_DIFY

    def stream_answer(
        self,
        app: Flask,
        user_id: str,
        user_query: str,
        messages: list[dict[str, Any]],
        provider_config: dict[str, Any],
    ) -> Generator[AskProviderChunk, None, None]:
        base_url = (get_config("DIFY_URL") or "").strip()
        api_key = (get_config("DIFY_API_KEY") or "").strip()
        if not base_url or not api_key:
            raise AskProviderConfigError("dify credentials not configured")

        config = provider_config.get("config") or {}
        if not isinstance(config, dict):
            config = {}

        payload: dict[str, Any] = {
            "query": user_query,
            "user": user_id,
            "response_mode": "streaming",
            "auto_generate_name": False,
            "inputs": config.get("inputs", {})
            if isinstance(config.get("inputs"), dict)
            else {},
            "files": [],
        }
        conversation_id = str(config.get("conversation_id") or "").strip()
        if conversation_id:
            payload["conversation_id"] = conversation_id

        url = base_url.rstrip("/") + "/chat-messages"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                stream=True,
                timeout=(5, _provider_timeout_seconds()),
            )
        except requests.Timeout as exc:
            raise AskProviderTimeoutError("dify request timeout") from exc
        except requests.RequestException as exc:
            raise AskProviderError(f"dify request failed: {exc}") from exc

        response = _raise_for_provider_response(response, self.provider)

        for raw_payload in _iter_sse_payloads(response):
            if not raw_payload or raw_payload.replace(" ", "") == "[DONE]":
                continue
            try:
                parsed = json.loads(raw_payload)
            except json.JSONDecodeError:
                app.logger.warning("Skip malformed dify payload: %s", raw_payload)
                continue

            event = str(parsed.get("event") or "").strip().lower()
            if event == "error":
                error_message = _extract_text(parsed) or str(parsed)
                raise AskProviderError(f"dify error: {error_message}")

            text = _extract_text(parsed)
            if text:
                yield AskProviderChunk(content=text)


class CozeAskProviderAdapter:
    provider = ASK_PROVIDER_COZE

    def stream_answer(
        self,
        app: Flask,
        user_id: str,
        user_query: str,
        messages: list[dict[str, Any]],
        provider_config: dict[str, Any],
    ) -> Generator[AskProviderChunk, None, None]:
        base_url = (get_config("COZE_URL") or "").strip()
        api_key = (get_config("COZE_API_KEY") or "").strip()
        if not base_url or not api_key:
            raise AskProviderConfigError("coze credentials not configured")

        config = provider_config.get("config") or {}
        if not isinstance(config, dict):
            config = {}

        bot_id = str(config.get("bot_id") or "").strip()
        api_path = str(config.get("api_path") or "/v3/chat").strip() or "/v3/chat"
        if api_path.startswith("http"):
            url = api_path
        else:
            url = base_url.rstrip("/") + "/" + api_path.lstrip("/")

        if api_path == "/v3/chat" and not bot_id:
            raise AskProviderConfigError("coze bot_id is required")

        payload: dict[str, Any] = {
            "stream": True,
            "user_id": user_id,
            "additional_messages": [
                {
                    "role": "user",
                    "content": user_query,
                    "content_type": "text",
                }
            ],
        }
        if bot_id:
            payload["bot_id"] = bot_id

        conversation_id = str(config.get("conversation_id") or "").strip()
        if conversation_id:
            payload["conversation_id"] = conversation_id

        extra_body = config.get("extra_body")
        if isinstance(extra_body, dict):
            payload.update(extra_body)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                stream=True,
                timeout=(5, _provider_timeout_seconds()),
            )
        except requests.Timeout as exc:
            raise AskProviderTimeoutError("coze request timeout") from exc
        except requests.RequestException as exc:
            raise AskProviderError(f"coze request failed: {exc}") from exc

        response = _raise_for_provider_response(response, self.provider)

        for raw_payload in _iter_sse_payloads(response):
            if not raw_payload or raw_payload.replace(" ", "") == "[DONE]":
                continue

            try:
                parsed = json.loads(raw_payload)
            except json.JSONDecodeError:
                app.logger.warning("Skip malformed coze payload: %s", raw_payload)
                continue

            event = str(parsed.get("event") or parsed.get("type") or "").lower()
            if "error" in event:
                error_message = _extract_text(parsed) or str(parsed)
                raise AskProviderError(f"coze error: {error_message}")
            if event in {"done", "message_end", "chat.completed"}:
                continue

            text = _extract_text(parsed)
            if text:
                yield AskProviderChunk(content=text)


def get_ask_provider_adapter(provider: str) -> AskProviderAdapter | None:
    provider = (provider or "").strip().lower()
    if provider == ASK_PROVIDER_DIFY:
        return DifyAskProviderAdapter()
    if provider == ASK_PROVIDER_COZE:
        return CozeAskProviderAdapter()
    return None


def stream_ask_provider_response(
    app: Flask,
    provider: str,
    user_id: str,
    user_query: str,
    messages: list[dict[str, Any]],
    provider_config: dict[str, Any],
) -> Generator[AskProviderChunk, None, None]:
    adapter = get_ask_provider_adapter(provider)
    if not adapter:
        raise AskProviderConfigError(f"unsupported provider: {provider}")
    yield from adapter.stream_answer(
        app, user_id, user_query, messages, provider_config
    )
