from datetime import datetime
from typing import Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
)

from task_cli.schemas import (
    TaskCreate,
    TaskPriority,
    TaskSort,
    TaskStatus,
    TaskUpdate,
)


class ListTasksToolArguments(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    overdue: bool = False
    due_within_days: int | None = Field(
        default=None,
        ge=1,
        le=365,
    )
    sort: TaskSort | None = None


class CreateTaskToolArguments(TaskCreate):
    model_config = ConfigDict(
        extra="forbid",
    )


class UpdateTaskToolArguments(TaskUpdate):
    model_config = ConfigDict(
        extra="forbid",
    )

    task_id: int = Field(
        gt=0,
    )


class RequestDeleteTaskToolArguments(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    task_id: int = Field(
        gt=0,
    )


class AssistantRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=1000,
    )

    conversation_id: int | None = Field(
        default=None,
        gt=0,
    )


class PendingActionRead(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    # 这是 PendingAction 的编号，不是 Task 的编号。
    action_id: int = Field(gt=0)

    # 当前项目只有删除任务需要服务器确认。
    action: Literal["delete_task"]

    task_id: int = Field(gt=0)

    # 返回前端的过期时间必须包含时区，
    # 浏览器才能正确显示同一个时间点。
    expires_at: AwareDatetime


class AssistantResult(BaseModel):
    # Service 的结果对象。
    # conversation_id 仍由 Router 管理，所以不放在这里。
    reply: str

    # None 表示这次回复没有产生待确认操作。
    # Python 的 None 序列化为 JSON 后就是 null。
    pending_action: PendingActionRead | None = None


class AssistantResponse(BaseModel):
    conversation_id: int = Field(gt=0)
    reply: str

    # 字段必须出现在 HTTP 响应模型中，
    # FastAPI 才会将它作为正式响应内容返回给前端。
    pending_action: PendingActionRead | None = None


class ConversationRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    created_at: datetime


class ConversationMessageRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    role: Literal[
        "user",
        "assistant",
    ]
    content: str
    created_at: datetime


class ActionResponse(BaseModel):
    action_id: int
    status: str
    message: str
