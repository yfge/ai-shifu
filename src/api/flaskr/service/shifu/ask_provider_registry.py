"""Ask provider registry and schema metadata."""

from typing import Any

from flaskr.service.config import get_config
from flaskr.service.shifu.shifu_draft_funcs import (
    ASK_PROVIDER_LLM,
    ASK_PROVIDER_DIFY,
    ASK_PROVIDER_COZE,
    ASK_PROVIDER_VOLC_KNOWLEDGE,
    ASK_PROVIDER_MODE_PROVIDER_ONLY,
    ASK_PROVIDER_MODE_PROVIDER_THEN_LLM,
    normalize_ask_provider_config,
)


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(value, (int, float)):
        return value != 0
    return False


def is_ask_provider_enabled() -> bool:
    """Whether external ask providers are enabled."""
    return _to_bool(get_config("ASK_PROVIDER_ENABLED"))


def get_default_ask_provider_config() -> dict[str, Any]:
    return {
        "provider": ASK_PROVIDER_LLM,
        "mode": ASK_PROVIDER_MODE_PROVIDER_ONLY,
        "config": {},
    }


def get_ask_provider_schema_registry() -> dict[str, dict[str, Any]]:
    """Return schema metadata for all supported ask providers."""
    return {
        ASK_PROVIDER_LLM: {
            "title": "LLM",
            "description": "Use built-in ask LLM only.",
            "default_config": {},
            "json_schema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
        ASK_PROVIDER_DIFY: {
            "title": "Dify",
            "description": "Route ask to Dify chat app with shifu-level config.",
            "default_config": {
                "base_url": "",
                "api_key": "",
                "conversation_id": "",
                "inputs": {},
            },
            "json_schema": {
                "type": "object",
                "properties": {
                    "base_url": {
                        "type": "string",
                        "title": "Base URL",
                        "description": "Dify base URL, e.g. https://api.dify.ai/v1",
                    },
                    "api_key": {
                        "type": "string",
                        "format": "password",
                        "title": "API Key",
                        "description": "Dify app API key.",
                    },
                    "conversation_id": {
                        "type": "string",
                        "title": "Conversation ID",
                        "description": "Optional existing Dify conversation_id.",
                    },
                    "inputs": {
                        "type": "object",
                        "title": "Inputs",
                        "description": "Optional Dify workflow inputs object.",
                    },
                },
                "required": ["base_url", "api_key"],
                "additionalProperties": True,
            },
        },
        ASK_PROVIDER_COZE: {
            "title": "Coze",
            "description": "Route ask to Coze bot chat API with shifu-level config.",
            "default_config": {
                "base_url": "",
                "api_key": "",
                "bot_id": "",
                "conversation_id": "",
                "api_path": "/v3/chat",
                "extra_body": {},
            },
            "json_schema": {
                "type": "object",
                "properties": {
                    "base_url": {
                        "type": "string",
                        "title": "Base URL",
                        "description": "Coze base URL, e.g. https://api.coze.com",
                    },
                    "api_key": {
                        "type": "string",
                        "format": "password",
                        "title": "API Key",
                        "description": "Coze personal access token.",
                    },
                    "bot_id": {
                        "type": "string",
                        "title": "Bot ID",
                        "description": "Coze bot identifier.",
                    },
                    "conversation_id": {
                        "type": "string",
                        "title": "Conversation ID",
                        "description": "Optional existing Coze conversation id.",
                    },
                    "api_path": {
                        "type": "string",
                        "title": "API Path",
                        "description": "Relative API path on base_url.",
                    },
                    "extra_body": {
                        "type": "object",
                        "title": "Extra Body",
                        "description": "Optional extra request body fields.",
                    },
                },
                "required": ["base_url", "api_key", "bot_id"],
                "additionalProperties": True,
            },
        },
        ASK_PROVIDER_VOLC_KNOWLEDGE: {
            "title": "Volcengine Knowledge Base",
            "description": "Route ask to Volcengine Knowledge Base search API.",
            "default_config": {
                "domain": "api-knowledgebase.mlp.cn-beijing.volces.com",
                "scheme": "https",
                "path": "/api/knowledge/collection/search_knowledge",
                "project": "default",
                "service": "air",
                "region": "cn-north-1",
                "account_id": "",
                "ak": "",
                "sk": "",
                "collection_name": "",
                "limit": 20,
                "dense_weight": 0.5,
                "image_query": "",
                "pre_processing": {},
                "post_processing": {},
                "query_param": {},
            },
            "json_schema": {
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "title": "Domain",
                        "description": "Volcengine KB domain host.",
                    },
                    "scheme": {
                        "type": "string",
                        "title": "Scheme",
                        "description": "Request scheme: http or https.",
                    },
                    "path": {
                        "type": "string",
                        "title": "Path",
                        "description": "API path for search endpoint.",
                    },
                    "project": {
                        "type": "string",
                        "title": "Project",
                        "description": "Volcengine KB project name.",
                    },
                    "service": {
                        "type": "string",
                        "title": "Service",
                        "description": "Signer service name (default: air).",
                    },
                    "region": {
                        "type": "string",
                        "title": "Region",
                        "description": "Signer region (default: cn-north-1).",
                    },
                    "account_id": {
                        "type": "string",
                        "title": "Account ID",
                        "description": "Volcengine account id for V-Account-Id header.",
                    },
                    "ak": {
                        "type": "string",
                        "format": "password",
                        "title": "Access Key",
                        "description": "Volcengine AK.",
                    },
                    "sk": {
                        "type": "string",
                        "format": "password",
                        "title": "Secret Key",
                        "description": "Volcengine SK.",
                    },
                    "collection_name": {
                        "type": "string",
                        "title": "Collection Name",
                        "description": "Knowledge base collection name.",
                    },
                    "limit": {
                        "type": "integer",
                        "title": "Limit",
                        "description": "Max recall results.",
                    },
                    "dense_weight": {
                        "type": "number",
                        "title": "Dense Weight",
                        "description": "Hybrid search dense weight.",
                    },
                    "image_query": {
                        "type": "string",
                        "title": "Image Query",
                        "description": "Optional image URL or base64 query.",
                    },
                    "pre_processing": {
                        "type": "object",
                        "title": "Pre Processing",
                        "description": "Optional pre_processing object.",
                    },
                    "post_processing": {
                        "type": "object",
                        "title": "Post Processing",
                        "description": "Optional post_processing object.",
                    },
                    "query_param": {
                        "type": "object",
                        "title": "Query Param",
                        "description": "Optional query_param object.",
                    },
                },
                "required": ["account_id", "ak", "sk", "collection_name"],
                "additionalProperties": True,
            },
        },
    }


def validate_ask_provider_specific_config(
    provider: str, config: Any
) -> tuple[bool, str | None]:
    """Lightweight validation against provider schema required fields."""
    registry = get_ask_provider_schema_registry()
    if provider not in registry:
        return False, "provider"
    if not isinstance(config, dict):
        return False, "config"

    schema = registry[provider].get("json_schema", {})
    required_fields = schema.get("required", [])
    for field in required_fields:
        value = config.get(field)
        if isinstance(value, str):
            if not value.strip():
                return False, field
        elif value is None:
            return False, field

    return True, None


def get_effective_ask_provider_config(raw_config: Any) -> dict[str, Any]:
    """
    Normalize persisted config and apply feature-flag gating.

    If ASK_PROVIDER_ENABLED=false, force llm provider.
    """
    normalized = normalize_ask_provider_config(raw_config)
    if not is_ask_provider_enabled() and normalized.get("provider") != ASK_PROVIDER_LLM:
        return get_default_ask_provider_config()
    return normalized


def get_ask_provider_metadata() -> dict[str, Any]:
    """Metadata endpoint payload for ask provider schema-driven UI."""
    feature_enabled = is_ask_provider_enabled()
    registry = get_ask_provider_schema_registry()

    providers: list[dict[str, Any]] = []
    for provider in [
        ASK_PROVIDER_LLM,
        ASK_PROVIDER_DIFY,
        ASK_PROVIDER_COZE,
        ASK_PROVIDER_VOLC_KNOWLEDGE,
    ]:
        if provider != ASK_PROVIDER_LLM and not feature_enabled:
            continue
        item = registry[provider]
        providers.append(
            {
                "provider": provider,
                "title": item.get("title", provider),
                "description": item.get("description", ""),
                "default_config": item.get("default_config", {}),
                "json_schema": item.get("json_schema", {}),
            }
        )

    return {
        "feature_enabled": feature_enabled,
        "default": get_default_ask_provider_config(),
        "modes": [
            {
                "value": ASK_PROVIDER_MODE_PROVIDER_ONLY,
                "title": "Provider Only",
            },
            {
                "value": ASK_PROVIDER_MODE_PROVIDER_THEN_LLM,
                "title": "Provider Then LLM",
            },
        ],
        "providers": providers,
    }
