import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from task_cli.conversation_service import (
    create_conversation,
    create_message,
)
from task_cli.models import User
from task_cli.schemas_ai import (
    AssistantRequest,
    ConversationMessageRead,
    ConversationRead,
)


def test_assistant_request_allows_optional_conversation_id() -> None:
    new_conversation_request = AssistantRequest(
        message="开始新会话",
    )

    continued_request = AssistantRequest(
        message="继续刚才的会话",
        conversation_id=5,
    )

    assert new_conversation_request.conversation_id is None
    assert continued_request.conversation_id == 5


def test_assistant_request_rejects_invalid_conversation_id() -> None:
    with pytest.raises(
        ValidationError,
    ):
        AssistantRequest(
            message="非法会话",
            conversation_id=0,
        )


def test_conversation_read_does_not_expose_owner_id(
    db_session: Session,
    user: User,
) -> None:
    conversation = create_conversation(
        session=db_session,
        owner_id=user.id,
    )

    data = ConversationRead.model_validate(conversation).model_dump()

    assert data == {
        "id": conversation.id,
        "created_at": conversation.created_at,
    }


def test_message_read_hides_internal_tool_fields(
    db_session: Session,
    user: User,
) -> None:
    conversation = create_conversation(
        session=db_session,
        owner_id=user.id,
    )

    message = create_message(
        session=db_session,
        conversation_id=conversation.id,
        owner_id=user.id,
        role="assistant",
        content="任务查询完成",
        tool_calls=[
            {
                "id": "call-1",
                "type": "function",
            }
        ],
    )

    data = ConversationMessageRead.model_validate(message).model_dump()

    assert data == {
        "id": message.id,
        "role": "assistant",
        "content": "任务查询完成",
        "created_at": message.created_at,
    }
