class AIServiceError(Exception):
    """AI 服务基础异常。"""


class AIToolError(AIServiceError):
    """AI 工具执行失败。"""


class AIProviderError(AIServiceError):
    """模型供应商调用失败。"""


class AIProviderTimeoutError(AIProviderError):
    """模型供应商请求超时。"""


class AIProviderRateLimitError(AIProviderError):
    """模型供应商请求被限流。"""


class AIProviderAuthenticationError(AIProviderError):
    """模型供应商认证失败。"""


class AIProviderConnectionError(AIProviderError):
    """无法连接模型供应商。"""


class AIProviderServerError(AIProviderError):
    """模型供应商服务端错误。"""
