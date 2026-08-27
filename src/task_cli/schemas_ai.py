from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from task_cli.schemas import TaskCreate, TaskPriority, TaskStatus, TaskUpdate


class ListTasksToolArguments(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    status: TaskStatus | None = None
    priority: TaskPriority | None = None


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


class AssistantResponse(BaseModel):
    reply: str


class ActionResponse(BaseModel):
    action_id: int
    status: str
    message: str
