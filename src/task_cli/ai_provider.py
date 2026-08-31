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


def call_ai_provider(
    messages: list[Any],
) -> Any:

    try:
        client = get_ai_client()
        model = get_ai_model()

        return client.chat.completions.create(
            model=model,
            messages=messages,
            tools=cast(
                list[ChatCompletionFunctionToolParam],
                TOOLS,
            ),
            tool_choice="auto",
            stream=False,
            extra_body={"thinking": {"type": "disabled"}},
        )

    except AIProviderError:
        raise

    except APITimeoutError as exc:
        raise AIProviderTimeoutError("DeepSeek API 请求超时") from exc

    except RateLimitError as exc:
        raise AIProviderRateLimitError("DeepSeek API 请求被限流") from exc

    except AuthenticationError as exc:
        raise AIProviderAuthenticationError("DeepSeek API 认证失败") from exc

    except InternalServerError as exc:
        raise AIProviderServerError("DeepSeek API 服务暂时不可用") from exc

    except APIConnectionError as exc:
        raise AIProviderConnectionError("无法连接 DeepSeek API") from exc

    except OpenAIError as exc:
        raise AIProviderError("DeepSeek API 调用失败") from exc
