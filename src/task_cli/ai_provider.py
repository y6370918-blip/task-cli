import logging
from time import perf_counter
from typing import Any, cast

from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    InternalServerError,
    OpenAIError,
    RateLimitError,
)
from openai.types.chat import (
    ChatCompletionFunctionToolParam,
)

from task_cli.ai_client import (
    get_ai_client,
    get_ai_model,
)
from task_cli.ai_exceptions import (
    AIProviderAuthenticationError,
    AIProviderConnectionError,
    AIProviderError,
    AIProviderRateLimitError,
    AIProviderServerError,
    AIProviderTimeoutError,
)
from task_cli.ai_tools import TOOLS

logger = logging.getLogger(__name__)


def _log_provider_failure(
    *,
    model: str | None,
    start_time: float,
    error: AIProviderError,
) -> None:
    duration_ms = (perf_counter() - start_time) * 1000

    logger.warning(
        "AI provider failed model=%s duration_ms=%.2f error_type=%s success=false",
        model or "unknown",
        duration_ms,
        type(error).__name__,
    )


def call_ai_provider(
    messages: list[Any],
) -> Any:
    start_time = perf_counter()
    model: str | None = None

    try:
        client = get_ai_client()
        model = get_ai_model()

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=cast(
                list[ChatCompletionFunctionToolParam],
                TOOLS,
            ),
            tool_choice="auto",
            stream=False,
            extra_body={
                "thinking": {
                    "type": "disabled",
                }
            },
        )

        duration_ms = (perf_counter() - start_time) * 1000

        usage = getattr(
            response,
            "usage",
            None,
        )

        logger.info(
            "AI provider completed "
            "model=%s "
            "duration_ms=%.2f "
            "input_tokens=%s "
            "output_tokens=%s "
            "total_tokens=%s "
            "success=true",
            model,
            duration_ms,
            getattr(
                usage,
                "prompt_tokens",
                None,
            ),
            getattr(
                usage,
                "completion_tokens",
                None,
            ),
            getattr(
                usage,
                "total_tokens",
                None,
            ),
        )

        return response

    except AIProviderError as exc:
        _log_provider_failure(
            model=model,
            start_time=start_time,
            error=exc,
        )
        raise

    except APITimeoutError as exc:
        error: AIProviderError = AIProviderTimeoutError("DeepSeek API 请求超时")
        _log_provider_failure(
            model=model,
            start_time=start_time,
            error=error,
        )
        raise error from exc

    except RateLimitError as exc:
        error = AIProviderRateLimitError("DeepSeek API 请求被限流")
        _log_provider_failure(
            model=model,
            start_time=start_time,
            error=error,
        )
        raise error from exc

    except AuthenticationError as exc:
        error = AIProviderAuthenticationError("DeepSeek API 认证失败")
        _log_provider_failure(
            model=model,
            start_time=start_time,
            error=error,
        )
        raise error from exc

    except InternalServerError as exc:
        error = AIProviderServerError("DeepSeek API 服务暂时不可用")
        _log_provider_failure(
            model=model,
            start_time=start_time,
            error=error,
        )
        raise error from exc

    except APIConnectionError as exc:
        error = AIProviderConnectionError("无法连接 DeepSeek API")
        _log_provider_failure(
            model=model,
            start_time=start_time,
            error=error,
        )
        raise error from exc

    except OpenAIError as exc:
        error = AIProviderError("DeepSeek API 调用失败")
        _log_provider_failure(
            model=model,
            start_time=start_time,
            error=error,
        )
        raise error from exc
