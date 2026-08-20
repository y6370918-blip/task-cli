import os

from dotenv import load_dotenv
from openai import OpenAI

from task_cli.ai_exceptions import (
    AIProviderError,
)


load_dotenv()


def get_ai_client() -> OpenAI:
    api_key = os.getenv(
        "DEEPSEEK_API_KEY"
    )

    if not api_key:
        raise AIProviderError(
            "未配置 DEEPSEEK_API_KEY"
        )

    return OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
    )


def get_ai_model() -> str:
    model = os.getenv(
        "DEEPSEEK_MODEL"
    )

    if not model:
        raise AIProviderError(
            "未配置 DEEPSEEK_MODEL"
        )

    return model