class AIServiceError(Exception):
    """AI 服务基础异常。"""


class AIToolError(AIServiceError):
    """AI 工具执行失败。"""


class AIProviderError(AIServiceError):
    """模型供应商调用失败。"""