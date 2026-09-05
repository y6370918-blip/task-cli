from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from task_cli.action_exceptions import (
    PendingActionAlreadyHandledError,
    PendingActionExpiredError,
    PendingActionNotFoundError,
)
from task_cli.action_service import (
    cancel_pending_action,
    confirm_pending_action,
)
from task_cli.ai_exceptions import AIServiceError
from task_cli.ai_service import (
    run_task_assistant_result,
)
from task_cli.auth_dependencies import (
    get_current_user,
)
from task_cli.conversation_exceptions import (
    ConversationNotFoundError,
)
from task_cli.conversation_service import (
    create_conversation,
    get_conversation,
    list_conversations,
    list_visible_conversation_messages,
)
from task_cli.dependencies import get_db
from task_cli.exceptions import (
    TaskNotFoundError,
)
from task_cli.models import User
from task_cli.schemas_ai import (
    ActionResponse,
    AssistantRequest,
    AssistantResponse,
    ConversationMessageRead,
    ConversationRead,
)

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
    current_user: User = Depends(get_current_user),
) -> AssistantResponse:
    try:
        if data.conversation_id is None:
            # 首次发送消息时创建会话。
            conversation = create_conversation(
                session=db,
                owner_id=current_user.id,
            )
        else:
            # 继续会话时仍需检查所有权。
            # 前端提供 conversation_id 不代表有权访问它。
            conversation = get_conversation(
                session=db,
                conversation_id=data.conversation_id,
                owner_id=current_user.id,
            )

    except ConversationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在",
        ) from None

    try:
        # 新入口返回 AssistantResult 对象，
        # 其中同时包含回复文字和待确认操作。
        result = run_task_assistant_result(
            db=db,
            owner_id=current_user.id,
            message=data.message,
            conversation_id=conversation.id,
        )

    except AIServiceError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI 服务暂时不可用",
        ) from None

    # Router 补充自己管理的 conversation_id。
    # pending_action 为 None 时，JSON 中会输出 null。
    return AssistantResponse(
        conversation_id=conversation.id,
        reply=result.reply,
        pending_action=result.pending_action,
    )


@router.get(
    "/conversations",
    response_model=list[ConversationRead],
)
def get_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ConversationRead]:
    conversations = list_conversations(
        session=db,
        owner_id=current_user.id,
    )

    return [
        ConversationRead.model_validate(conversation) for conversation in conversations
    ]


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[ConversationMessageRead],
)
def get_conversation_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ConversationMessageRead]:
    try:
        messages = list_visible_conversation_messages(
            session=db,
            conversation_id=conversation_id,
            owner_id=current_user.id,
        )

    except ConversationNotFoundError:
        raise HTTPException(
            status_code=(status.HTTP_404_NOT_FOUND),
            detail="会话不存在",
        ) from None

    return [ConversationMessageRead.model_validate(message) for message in messages]


@router.post(
    "/actions/{action_id}/confirm",
    response_model=ActionResponse,
)
def confirm_action(
    action_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
        ) from None

    except PendingActionExpiredError:
        raise HTTPException(
            status_code=410,
            detail="待确认操作已经过期",
        ) from None

    except PendingActionAlreadyHandledError:
        raise HTTPException(
            status_code=409,
            detail="该操作已经被处理",
        ) from None

    except TaskNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="任务不存在",
        ) from None

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
    current_user: User = Depends(get_current_user),
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
        ) from None

    except PendingActionExpiredError:
        raise HTTPException(
            status_code=410,
            detail="待确认操作已经过期",
        ) from None

    except PendingActionAlreadyHandledError:
        raise HTTPException(
            status_code=409,
            detail="该操作已经被处理",
        ) from None

    return ActionResponse(
        action_id=action.id,
        status=action.status,
        message="操作已经取消",
    )
