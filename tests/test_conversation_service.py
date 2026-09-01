import pytest
from sqlalchemy.orm import Session

from task_cli.conversation_exceptions import (
    ConversationNotFoundError,
)
from task_cli.conversation_service import (
    create_conversation,
    create_message,
    get_conversation,
    list_conversation_messages,
    list_conversations,
)
from task_cli.models import User


def test_create_and_list_conversations_for_owner(
    db_session: Session,
    user: User,
    other_user: User,
) -> None:
    first_conversation = create_conversation(
        session=db_session,
        owner_id=user.id,
    )

    create_conversation(
        session=db_session,
        owner_id=other_user.id,
    )

    latest_conversation = create_conversation(
        session=db_session,
        owner_id=user.id,
    )

    conversations = list_conversations(
        session=db_session,
        owner_id=user.id,
    )

    assert [conversation.id for conversation in conversations] == [
        latest_conversation.id,
        first_conversation.id,
    ]


def test_get_conversation_returns_owned_conversation(
    db_session: Session,
    user: User,
) -> None:
    conversation = create_conversation(
        session=db_session,
        owner_id=user.id,
    )

    result = get_conversation(
        session=db_session,
        conversation_id=conversation.id,
        owner_id=user.id,
    )

    assert result.id == conversation.id
    assert result.owner_id == user.id


def test_get_conversation_hides_other_users_conversation(
    db_session: Session,
    user: User,
    other_user: User,
) -> None:
    conversation = create_conversation(
        session=db_session,
        owner_id=other_user.id,
    )

    with pytest.raises(
        ConversationNotFoundError,
    ):
        get_conversation(
            session=db_session,
            conversation_id=conversation.id,
            owner_id=user.id,
        )


def test_conversation_history_keeps_protocol_and_order(
    db_session: Session,
    user: User,
) -> None:
    conversation = create_conversation(
        session=db_session,
        owner_id=user.id,
    )

    create_message(
        session=db_session,
        conversation_id=conversation.id,
        owner_id=user.id,
        role="user",
        content="查询我的任务",
    )

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

    assistant_tool_message = create_message(
        session=db_session,
        conversation_id=conversation.id,
        owner_id=user.id,
        role="assistant",
        content=None,
        tool_calls=tool_calls,
    )

    tool_message = create_message(
        session=db_session,
        conversation_id=conversation.id,
        owner_id=user.id,
        role="tool",
        content='{"success": true, "tasks": []}',
        tool_call_id="call-list-1",
    )

    final_message = create_message(
        session=db_session,
        conversation_id=conversation.id,
        owner_id=user.id,
        role="assistant",
        content="你目前没有任务。",
    )

    history = list_conversation_messages(
        session=db_session,
        conversation_id=conversation.id,
        owner_id=user.id,
        limit=3,
    )

    assert [message.id for message in history] == [
        assistant_tool_message.id,
        tool_message.id,
        final_message.id,
    ]

    assert history[0].tool_calls == tool_calls
    assert history[1].tool_call_id == "call-list-1"
    assert history[2].content == "你目前没有任务。"


def test_message_operations_hide_other_users_conversation(
    db_session: Session,
    user: User,
    other_user: User,
) -> None:
    conversation = create_conversation(
        session=db_session,
        owner_id=other_user.id,
    )

    with pytest.raises(
        ConversationNotFoundError,
    ):
        create_message(
            session=db_session,
            conversation_id=conversation.id,
            owner_id=user.id,
            role="user",
            content="尝试写入其他用户的会话",
        )

    with pytest.raises(
        ConversationNotFoundError,
    ):
        list_conversation_messages(
            session=db_session,
            conversation_id=conversation.id,
            owner_id=user.id,
        )
