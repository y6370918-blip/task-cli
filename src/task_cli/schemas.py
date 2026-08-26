from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

TaskStatus = Literal[
    "pending",
    "doing",
    "done",
]

TaskPriority = Literal[
    "low",
    "medium",
    "high",
]


class TaskCreate(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=100,
    )

    priority: TaskPriority = "medium"

    description: str | None = Field(
        default=None,
        max_length=500,
    )


class TaskUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    description: str | None = None

    status: TaskStatus | None = None

    priority: TaskPriority | None = None

    @field_validator("priority")
    @classmethod
    def priority_cannot_be_null(
        cls,
        value: TaskPriority | None,
    ) -> TaskPriority:
        if value is None:
            raise ValueError("priority cannot be null")

        return value


class TaskRead(BaseModel):
    id: int
    title: str
    description: str | None
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    priority: TaskPriority
