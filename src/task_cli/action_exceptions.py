class PendingActionError(Exception):
    """待确认操作基础异常。"""


class PendingActionNotFoundError(
    PendingActionError
):
    """待确认操作不存在。"""


class PendingActionExpiredError(
    PendingActionError
):
    """待确认操作已经过期。"""


class PendingActionAlreadyHandledError(
    PendingActionError
):
    """待确认操作已经被处理。"""