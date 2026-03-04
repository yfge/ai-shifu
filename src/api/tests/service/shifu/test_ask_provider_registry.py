from flaskr.service.shifu import ask_provider_registry as module


def test_validate_dify_requires_shifu_level_base_url_and_api_key():
    is_valid, field = module.validate_ask_provider_specific_config(
        "dify", {"conversation_id": "conv-1"}
    )

    assert is_valid is False
    assert field == "base_url"


def test_validate_dify_shifu_level_config_success():
    is_valid, field = module.validate_ask_provider_specific_config(
        "dify",
        {
            "base_url": "https://dify.example.com/v1",
            "api_key": "dify-key",
            "conversation_id": "conv-1",
        },
    )

    assert is_valid is True
    assert field is None


def test_validate_coze_requires_base_url_api_key_and_bot_id():
    is_valid, field = module.validate_ask_provider_specific_config(
        "coze",
        {
            "base_url": "https://coze.example.com",
            "api_key": "coze-key",
        },
    )

    assert is_valid is False
    assert field == "bot_id"


def test_ask_provider_metadata_contains_shifu_level_defaults(monkeypatch):
    monkeypatch.setattr(
        module,
        "get_config",
        lambda key: "true" if key == "ASK_PROVIDER_ENABLED" else None,
    )

    metadata = module.get_ask_provider_metadata()
    providers = {item["provider"]: item for item in metadata.get("providers", [])}

    dify = providers.get("dify", {})
    coze = providers.get("coze", {})

    assert "base_url" in dify.get("default_config", {})
    assert "api_key" in dify.get("default_config", {})
    assert "base_url" in coze.get("default_config", {})
    assert "api_key" in coze.get("default_config", {})
