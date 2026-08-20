from task_cli.action_exceptions import (
    PendingActionAlreadyHandledError,
    PendingActionExpiredError,
    PendingActionNotFoundError,
)

from task_cli.action_service import (
    cancel_pending_action,
    confirm_pending_action,
)

from task_cli.exceptions import (
    TaskNotFoundError,
)
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from sqlalchemy.orm import Session

from task_cli.ai_service import (
    run_task_assistant,
)
from task_cli.auth_dependencies import (
    get_current_user,
)
from task_cli.dependencies import get_db
from task_cli.models import User
from task_cli.schemas_ai import (
    AssistantRequest,
    AssistantResponse,
    ActionResponse,
)
from task_cli.ai_exceptions import AIServiceError

router = APIRouter(
    prefix="/assistant",
    tags=["assistant"],
)


@router.post(
    "/",
    response_model=AssistantResponse,
)
def assistant(
    data: AssistantRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
) -> AssistantResponse:

    try:
        reply = run_task_assistant(
            db=db,
            owner_id=current_user.id,
            message=data.message,
        )

    except AIServiceError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI 服务暂时不可用",
        )

    return AssistantResponse(
        reply=reply
    )

@router.post(
    "/actions/{action_id}/confirm",
    response_model=ActionResponse,
)
def confirm_action(
    action_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
) -> ActionResponse:

    try:
        action = confirm_pending_action(
            session=db,
            action_id=action_id,
            owner_id=current_user.id,
        )

    except PendingActionNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="待确认操作不存在",
        )

    except PendingActionExpiredError:
        raise HTTPException(
            status_code=410,
            detail="待确认操作已经过期",
        )

    except PendingActionAlreadyHandledError:
        raise HTTPException(
            status_code=409,
            detail="该操作已经被处理",
        )

    except TaskNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="任务不存在",
        )

    return ActionResponse(
        action_id=action.id,
        status=action.status,
        message="操作已经确认并执行",
    )

@router.post(
    "/actions/{action_id}/cancel",
    response_model=ActionResponse,
)
def cancel_action(
    action_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
) -> ActionResponse:

    try:
        action = cancel_pending_action(
            session=db,
            action_id=action_id,
            owner_id=current_user.id,
        )

    except PendingActionNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="待确认操作不存在",
        )

    except PendingActionExpiredError:
        raise HTTPException(
            status_code=410,
            detail="待确认操作已经过期",
        )

    except PendingActionAlreadyHandledError:
        raise HTTPException(
            status_code=409,
            detail="该操作已经被处理",
        )

    return ActionResponse(
        action_id=action.id,
        status=action.status,
        message="操作已经取消",
    )
