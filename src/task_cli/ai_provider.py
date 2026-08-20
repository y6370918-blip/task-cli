from typing import Any

from openai import OpenAIError

from task_cli.ai_client import (
    get_ai_client,
    get_ai_model,
)
from task_cli.ai_exceptions import (
    AIProviderError,
)
from task_cli.ai_tools import TOOLS


def call_ai_provider(
    messages: list[Any],
) -> Any:

    try:
        client = get_ai_client()
        model = get_ai_model()

        return (
            client.chat.completions.create(
                model=model,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                stream=False,
                extra_body={
                    "thinking": {
                        "type": "disabled"
                    }
                },
            )
        )

    except AIProviderError:
        raise

    except OpenAIError as exc:
        raise AIProviderError(
            "DeepSeek API 调用失败"
        ) from exc