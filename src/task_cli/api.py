import time
from fastapi import FastAPI,Request
from fastapi.dependencies.utils import request_body_to_args
from task_cli.routers import tasks,auth,assistant
from task_cli.exceptions import TaskNotFoundError
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from task_cli.database import create_tables


@asynccontextmanager
async def lifespan(app: FastAPI):

    yield

app = FastAPI(
    title="Task API",
    lifespan=lifespan
)

@app.exception_handler(
    TaskNotFoundError
)
async def task_not_found_handler(
    request:Request,
    exc:TaskNotFoundError,
):
    return JSONResponse(
        status_code=404,
        content={
            "error": "TASK_NOT_FOUND",
            "message": f"Task {exc.task_id} not found",
        },
    )


@app.get("/")
def root():
    return{
        "message":"Task API running"
    }

@app.middleware("http")
async def log_requests(
    request: Request,
    call_next,
):

    start_time = time.time()


    response = await call_next(
        request
    )


    process_time = (
        time.time()
        -
        start_time
    )


    print(
        f"{request.method} "
        f"{request.url.path} "
        f"{process_time:.4f}s"
    )


    return response



app.include_router(
    tasks.router
)
app.include_router(auth.router)
app.include_router(assistant.router)