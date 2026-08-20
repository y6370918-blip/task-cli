from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from task_cli.schemas import TaskStatus


class ListTasksToolArguments(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    status: TaskStatus | None = None


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
