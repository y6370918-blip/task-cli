import os
from math import isfinite

from dotenv import load_dotenv
from openai import OpenAI

from task_cli.ai_exceptions import AIProviderError

load_dotenv()


def _get_timeout_seconds() -> float:
    raw_timeout = os.getenv(
        "DEEPSEEK_TIMEOUT_SECONDS",
        "30",
    )

    try:
        timeout_seconds = float(raw_timeout)
    except ValueError as exc:
        raise AIProviderError(
            "DeepSeek 客户端配置无效：DEEPSEEK_TIMEOUT_SECONDS"
        ) from exc

    if not isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise AIProviderError("DeepSeek 客户端配置无效：DEEPSEEK_TIMEOUT_SECONDS")

    return timeout_seconds


def _get_max_retries() -> int:
    raw_max_retries = os.getenv(
        "DEEPSEEK_MAX_RETRIES",
        "2",
    )

    try:
        max_retries = int(raw_max_retries)
    except ValueError as exc:
        raise AIProviderError("DeepSeek 客户端配置无效：DEEPSEEK_MAX_RETRIES") from exc

    if max_retries < 0 or max_retries > 5:
        raise AIProviderError("DeepSeek 客户端配置无效：DEEPSEEK_MAX_RETRIES")

    return max_retries


def get_ai_client() -> OpenAI:
    api_key = os.getenv("DEEPSEEK_API_KEY")

    if not api_key:
        raise AIProviderError("未配置 DEEPSEEK_API_KEY")

    return OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
        timeout=_get_timeout_seconds(),
        max_retries=_get_max_retries(),
    )


def get_ai_model() -> str:
    model = os.getenv("DEEPSEEK_MODEL")

    if not model:
        raise AIProviderError("未配置 DEEPSEEK_MODEL")

    return model
