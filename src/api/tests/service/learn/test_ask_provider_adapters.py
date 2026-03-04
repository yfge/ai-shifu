import pytest
import requests

from flaskr.service.learn import ask_provider_adapters as module
from flaskr.service.learn.ask_provider_adapters import (
    common,
    coze_adapter,
    dify_adapter,
)


class _FakeResponse:
    def __init__(self, lines=None, status_code=200, text="", http_error=None):
        self._lines = lines or []
        self.status_code = status_code
        self.text = text
        self._http_error = http_error

    def iter_lines(self, decode_unicode=True):
        _ = decode_unicode
        for line in self._lines:
            yield line

    def raise_for_status(self):
        if self._http_error is not None:
            raise self._http_error


def test_dify_adapter_streams_success_content(app, monkeypatch):
    adapter = module.DifyAskProviderAdapter()

    monkeypatch.setattr(
        dify_adapter,
        "get_config",
        lambda key: {
            "DIFY_URL": "https://dify.example.com",
            "DIFY_API_KEY": "test-key",
            "ASK_PROVIDER_TIMEOUT_SECONDS": 20,
        }.get(key),
    )
    monkeypatch.setattr(
        common,
        "get_config",
        lambda key: {
            "ASK_PROVIDER_TIMEOUT_SECONDS": 20,
        }.get(key),
    )
    monkeypatch.setattr(
        dify_adapter.requests,
        "post",
        lambda *_args, **_kwargs: _FakeResponse(
            lines=[
                'data: {"event":"message","answer":"hello"}',
                'data: {"event":"message","answer":" world"}',
                "data: [DONE]",
            ]
        ),
    )

    chunks = list(
        adapter.stream_answer(
            app=app,
            user_id="user-1",
            user_query="hello",
            messages=[],
            provider_config={"config": {}},
        )
    )

    assert [chunk.content for chunk in chunks] == ["hello", " world"]


def test_coze_adapter_timeout_raises_timeout_error(app, monkeypatch):
    adapter = module.CozeAskProviderAdapter()

    monkeypatch.setattr(
        coze_adapter,
        "get_config",
        lambda key: {
            "COZE_URL": "https://coze.example.com",
            "COZE_API_KEY": "test-key",
            "ASK_PROVIDER_TIMEOUT_SECONDS": 20,
        }.get(key),
    )
    monkeypatch.setattr(
        common,
        "get_config",
        lambda key: {
            "ASK_PROVIDER_TIMEOUT_SECONDS": 20,
        }.get(key),
    )

    def _raise_timeout(*_args, **_kwargs):
        raise requests.Timeout("timeout")

    monkeypatch.setattr(coze_adapter.requests, "post", _raise_timeout)

    with pytest.raises(module.AskProviderTimeoutError):
        list(
            adapter.stream_answer(
                app=app,
                user_id="user-1",
                user_query="hello",
                messages=[],
                provider_config={"config": {"bot_id": "bot-1"}},
            )
        )


def test_stream_ask_provider_response_raises_error_for_unsupported_provider(app):
    with pytest.raises(module.AskProviderConfigError):
        list(
            module.stream_ask_provider_response(
                app=app,
                provider="unsupported",
                user_id="user-1",
                user_query="hello",
                messages=[],
                provider_config={"config": {}},
            )
        )


def test_coze_adapter_http_error_raises_provider_error(app, monkeypatch):
    adapter = module.CozeAskProviderAdapter()

    monkeypatch.setattr(
        coze_adapter,
        "get_config",
        lambda key: {
            "COZE_URL": "https://coze.example.com",
            "COZE_API_KEY": "test-key",
            "ASK_PROVIDER_TIMEOUT_SECONDS": 20,
        }.get(key),
    )
    monkeypatch.setattr(
        common,
        "get_config",
        lambda key: {
            "ASK_PROVIDER_TIMEOUT_SECONDS": 20,
        }.get(key),
    )

    http_error = requests.HTTPError("boom")
    monkeypatch.setattr(
        coze_adapter.requests,
        "post",
        lambda *_args, **_kwargs: _FakeResponse(
            text="coze bad request",
            status_code=400,
            http_error=http_error,
        ),
    )

    with pytest.raises(module.AskProviderError, match="coze request failed"):
        list(
            adapter.stream_answer(
                app=app,
                user_id="user-1",
                user_query="hello",
                messages=[],
                provider_config={"config": {"bot_id": "bot-1"}},
            )
        )
