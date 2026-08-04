from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

TaskStatus = Literal[
    "pending",
    "doing",
    "done",
]


class TaskCreate(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=100,
    )

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


class TaskRead(BaseModel):
    id: int
    title: str
    description: str | None
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
