import logging
from types import SimpleNamespace

import httpx2
import pytest
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    InternalServerError,
    OpenAIError,
    RateLimitError,
)

import task_cli.ai_provider as ai_provider
from task_cli.ai_exceptions import (
    AIProviderAuthenticationError,
    AIProviderConnectionError,
    AIProviderError,
    AIProviderRateLimitError,
    AIProviderServerError,
    AIProviderTimeoutError,
)


def test_call_ai_provider_converts_timeout_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = httpx2.Request(
        "POST",
        "https://api.deepseek.com/chat/completions",
    )
    sdk_error = APITimeoutError(
        request=request,
    )

    def raise_timeout(
        **kwargs: object,
    ) -> None:
        raise sdk_error

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=raise_timeout,
            ),
        ),
    )

    monkeypatch.setattr(
        ai_provider,
        "get_ai_client",
        lambda: fake_client,
    )
    monkeypatch.setattr(
        ai_provider,
        "get_ai_model",
        lambda: "deepseek-chat",
    )

    with pytest.raises(
        AIProviderTimeoutError,
        match="DeepSeek API 请求超时",
    ) as exc_info:
        ai_provider.call_ai_provider(
            messages=[],
        )

    assert exc_info.value.__cause__ is sdk_error


@pytest.mark.parametrize(
    (
        "sdk_error",
        "expected_error_type",
        "expected_message",
    ),
    [
        (
            APIConnectionError(
                request=httpx2.Request(
                    "POST",
                    "https://api.deepseek.com/chat/completions",
                ),
            ),
            AIProviderConnectionError,
            "无法连接 DeepSeek API",
        ),
        (
            RateLimitError(
                "rate limited",
                response=httpx2.Response(
                    429,
                    request=httpx2.Request(
                        "POST",
                        "https://api.deepseek.com/chat/completions",
                    ),
                ),
                body=None,
            ),
            AIProviderRateLimitError,
            "DeepSeek API 请求被限流",
        ),
        (
            AuthenticationError(
                "invalid api key",
                response=httpx2.Response(
                    401,
                    request=httpx2.Request(
                        "POST",
                        "https://api.deepseek.com/chat/completions",
                    ),
                ),
                body=None,
            ),
            AIProviderAuthenticationError,
            "DeepSeek API 认证失败",
        ),
        (
            InternalServerError(
                "provider unavailable",
                response=httpx2.Response(
                    500,
                    request=httpx2.Request(
                        "POST",
                        "https://api.deepseek.com/chat/completions",
                    ),
                ),
                body=None,
            ),
            AIProviderServerError,
            "DeepSeek API 服务暂时不可用",
        ),
    ],
)
def test_call_ai_provider_classifies_sdk_errors(
    monkeypatch: pytest.MonkeyPatch,
    sdk_error: OpenAIError,
    expected_error_type: type[AIProviderError],
    expected_message: str,
) -> None:
    def raise_sdk_error(
        **kwargs: object,
    ) -> None:
        raise sdk_error

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=raise_sdk_error,
            ),
        ),
    )

    monkeypatch.setattr(
        ai_provider,
        "get_ai_client",
        lambda: fake_client,
    )
    monkeypatch.setattr(
        ai_provider,
        "get_ai_model",
        lambda: "deepseek-chat",
    )

    with pytest.raises(
        expected_error_type,
        match=expected_message,
    ) as exc_info:
        ai_provider.call_ai_provider(
            messages=[],
        )

    assert exc_info.value.__cause__ is sdk_error


def test_call_ai_provider_keeps_generic_error_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = httpx2.Request(
        "POST",
        "https://api.deepseek.com/chat/completions",
    )
    sdk_error = APIStatusError(
        "unexpected provider response",
        response=httpx2.Response(
            418,
            request=request,
        ),
        body=None,
    )

    def raise_sdk_error(
        **kwargs: object,
    ) -> None:
        raise sdk_error

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=raise_sdk_error,
            ),
        ),
    )

    monkeypatch.setattr(
        ai_provider,
        "get_ai_client",
        lambda: fake_client,
    )
    monkeypatch.setattr(
        ai_provider,
        "get_ai_model",
        lambda: "deepseek-chat",
    )

    with pytest.raises(
        AIProviderError,
        match="DeepSeek API 调用失败",
    ) as exc_info:
        ai_provider.call_ai_provider(
            messages=[],
        )

    assert type(exc_info.value) is AIProviderError
    assert exc_info.value.__cause__ is sdk_error


def test_call_ai_provider_logs_success_metrics(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    response = SimpleNamespace(
        usage=SimpleNamespace(
            prompt_tokens=120,
            completion_tokens=35,
            total_tokens=155,
        ),
    )

    def return_response(
        **kwargs: object,
    ) -> object:
        return response

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=return_response,
            ),
        ),
    )
    times = iter(
        [
            10.0,
            10.125,
        ]
    )

    monkeypatch.setattr(
        ai_provider,
        "get_ai_client",
        lambda: fake_client,
    )
    monkeypatch.setattr(
        ai_provider,
        "get_ai_model",
        lambda: "deepseek-chat",
    )
    monkeypatch.setattr(
        ai_provider,
        "perf_counter",
        lambda: next(times),
        raising=False,
    )

    with caplog.at_level(
        logging.INFO,
        logger="task_cli.ai_provider",
    ):
        result = ai_provider.call_ai_provider(
            messages=[],
        )

    assert result is response
    assert (
        "AI provider completed "
        "model=deepseek-chat "
        "duration_ms=125.00 "
        "input_tokens=120 "
        "output_tokens=35 "
        "total_tokens=155 "
        "success=true"
    ) in caplog.messages


def test_call_ai_provider_logs_sanitized_failure_metrics(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    sensitive_provider_detail = "sensitive-provider-response-body"
    sdk_error = APIConnectionError(
        message=sensitive_provider_detail,
        request=httpx2.Request(
            "POST",
            "https://api.deepseek.com/chat/completions",
        ),
    )

    def raise_connection_error(
        **kwargs: object,
    ) -> None:
        raise sdk_error

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=raise_connection_error,
            ),
        ),
    )
    times = iter(
        [
            20.0,
            20.25,
        ]
    )

    monkeypatch.setattr(
        ai_provider,
        "get_ai_client",
        lambda: fake_client,
    )
    monkeypatch.setattr(
        ai_provider,
        "get_ai_model",
        lambda: "deepseek-chat",
    )
    monkeypatch.setattr(
        ai_provider,
        "perf_counter",
        lambda: next(times),
    )

    with caplog.at_level(
        logging.WARNING,
        logger="task_cli.ai_provider",
    ):
        with pytest.raises(
            AIProviderConnectionError,
        ):
            ai_provider.call_ai_provider(
                messages=[],
            )

    assert (
        "AI provider failed "
        "model=deepseek-chat "
        "duration_ms=250.00 "
        "error_type=AIProviderConnectionError "
        "success=false"
    ) in caplog.messages

    assert sensitive_provider_detail not in caplog.text


def test_call_ai_provider_handles_missing_usage(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    response = SimpleNamespace()

    def return_response(
        **kwargs: object,
    ) -> object:
        return response

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=return_response,
            ),
        ),
    )
    times = iter(
        [
            30.0,
            30.01,
        ]
    )

    monkeypatch.setattr(
        ai_provider,
        "get_ai_client",
        lambda: fake_client,
    )
    monkeypatch.setattr(
        ai_provider,
        "get_ai_model",
        lambda: "deepseek-chat",
    )
    monkeypatch.setattr(
        ai_provider,
        "perf_counter",
        lambda: next(times),
    )

    with caplog.at_level(
        logging.INFO,
        logger="task_cli.ai_provider",
    ):
        result = ai_provider.call_ai_provider(
            messages=[],
        )

    assert result is response
    assert (
        "AI provider completed "
        "model=deepseek-chat "
        "duration_ms=10.00 "
        "input_tokens=None "
        "output_tokens=None "
        "total_tokens=None "
        "success=true"
    ) in caplog.messages
