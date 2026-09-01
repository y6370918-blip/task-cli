import time
from collections.abc import (
    AsyncIterator,
    Awaitable,
    Callable,
)
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse

from task_cli.exceptions import TaskNotFoundError
from task_cli.routers import assistant, auth, tasks


@asynccontextmanager
async def lifespan(
    _app: FastAPI,
) -> AsyncIterator[None]:
    yield


app = FastAPI(title="Task API", lifespan=lifespan)


@app.exception_handler(TaskNotFoundError)
async def task_not_found_handler(
    _request: Request,
    exc: TaskNotFoundError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "TASK_NOT_FOUND",
            "message": (f"Task {exc.task_id} not found"),
        },
    )


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Task API running"}


@app.middleware("http")
async def log_requests(
    request: Request,
    call_next: Callable[
        [Request],
        Awaitable[Response],
    ],
) -> Response:

    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time

    print(f"{request.method} {request.url.path} {process_time:.4f}s")

    return response


app.include_router(tasks.router)
app.include_router(auth.router)
app.include_router(assistant.router)
