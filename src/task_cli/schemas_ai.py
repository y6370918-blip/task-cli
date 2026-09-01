from datetime import datetime
from typing import Literal

from pydantic import (
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


class AssistantResponse(BaseModel):
    conversation_id: int = Field(
        gt=0,
    )
    reply: str


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
