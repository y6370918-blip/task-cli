import pytest

import task_cli.ai_client as ai_client
from task_cli.ai_exceptions import AIProviderError


def test_get_ai_client_configures_timeout_and_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_arguments: dict[str, object] = {}
    fake_client = object()

    def fake_openai(
        **kwargs: object,
    ) -> object:
        captured_arguments.update(kwargs)
        return fake_client

    monkeypatch.setenv(
        "DEEPSEEK_API_KEY",
        "test-api-key",
    )
    monkeypatch.setenv(
        "DEEPSEEK_TIMEOUT_SECONDS",
        "30",
    )
    monkeypatch.setenv(
        "DEEPSEEK_MAX_RETRIES",
        "2",
    )
    monkeypatch.setattr(
        ai_client,
        "OpenAI",
        fake_openai,
    )

    result = ai_client.get_ai_client()

    assert result is fake_client
    assert captured_arguments == {
        "api_key": "test-api-key",
        "base_url": "https://api.deepseek.com",
        "timeout": 30.0,
        "max_retries": 2,
    }


@pytest.mark.parametrize(
    (
        "environment_name",
        "environment_value",
    ),
    [
        (
            "DEEPSEEK_TIMEOUT_SECONDS",
            "not-a-number",
        ),
        (
            "DEEPSEEK_TIMEOUT_SECONDS",
            "0",
        ),
        (
            "DEEPSEEK_TIMEOUT_SECONDS",
            "-1",
        ),
        (
            "DEEPSEEK_MAX_RETRIES",
            "not-an-integer",
        ),
        (
            "DEEPSEEK_MAX_RETRIES",
            "-1",
        ),
        (
            "DEEPSEEK_MAX_RETRIES",
            "6",
        ),
    ],
)
def test_get_ai_client_rejects_invalid_configuration(
    monkeypatch: pytest.MonkeyPatch,
    environment_name: str,
    environment_value: str,
) -> None:
    def fake_openai(
        **kwargs: object,
    ) -> object:
        return object()

    monkeypatch.setenv(
        "DEEPSEEK_API_KEY",
        "test-api-key",
    )
    monkeypatch.setenv(
        environment_name,
        environment_value,
    )
    monkeypatch.setattr(
        ai_client,
        "OpenAI",
        fake_openai,
    )

    with pytest.raises(
        AIProviderError,
        match="DeepSeek 客户端配置无效",
    ):
        ai_client.get_ai_client()


def test_get_ai_client_uses_safe_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_arguments: dict[str, object] = {}

    def fake_openai(
        **kwargs: object,
    ) -> object:
        captured_arguments.update(kwargs)
        return object()

    monkeypatch.setenv(
        "DEEPSEEK_API_KEY",
        "test-api-key",
    )
    monkeypatch.delenv(
        "DEEPSEEK_TIMEOUT_SECONDS",
        raising=False,
    )
    monkeypatch.delenv(
        "DEEPSEEK_MAX_RETRIES",
        raising=False,
    )
    monkeypatch.setattr(
        ai_client,
        "OpenAI",
        fake_openai,
    )

    ai_client.get_ai_client()

    assert captured_arguments["timeout"] == 30.0
    assert captured_arguments["max_retries"] == 2
