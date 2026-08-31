import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from task_cli.models import (
    Conversation,
    Message,
    User,
)


def test_conversation_persists_ordered_tool_history(
    db_session: Session,
    user: User,
) -> None:
    conversation = Conversation(
        owner_id=user.id,
    )

    db_session.add(conversation)
    db_session.commit()
    db_session.refresh(conversation)

    tool_calls = [
        {
            "id": "call-list-1",
            "type": "function",
            "function": {
                "name": "list_tasks",
                "arguments": "{}",
            },
        }
    ]

    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content="查询我的任务",
    )
    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=None,
        tool_calls=tool_calls,
    )
    tool_message = Message(
        conversation_id=conversation.id,
        role="tool",
        content='{"success": true}',
        tool_call_id="call-list-1",
    )

    db_session.add_all(
        [
            user_message,
            assistant_message,
            tool_message,
        ]
    )
    db_session.commit()

    messages = list(
        db_session.scalars(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.id)
        )
    )

    assert conversation.owner_id == user.id
    assert conversation.created_at is not None

    assert [message.role for message in messages] == [
        "user",
        "assistant",
        "tool",
    ]

    assert messages[1].content is None
    assert messages[1].tool_calls == tool_calls
    assert messages[2].tool_call_id == "call-list-1"


def test_message_rejects_persisted_system_role(
    db_session: Session,
    user: User,
) -> None:
    conversation = Conversation(
        owner_id=user.id,
    )

    db_session.add(conversation)
    db_session.commit()
    db_session.refresh(conversation)

    message = Message(
        conversation_id=conversation.id,
        role="system",
        content="不允许持久化的系统消息",
    )

    db_session.add(message)

    with pytest.raises(
        IntegrityError,
    ):
        db_session.commit()

    db_session.rollback()
