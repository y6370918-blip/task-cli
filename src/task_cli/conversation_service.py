from sqlalchemy import select
from sqlalchemy.orm import Session

from task_cli.conversation_exceptions import (
    ConversationNotFoundError,
)
from task_cli.models import (
    Conversation,
    Message,
)


def create_conversation(
    session: Session,
    owner_id: int,
) -> Conversation:
    conversation = Conversation(
        owner_id=owner_id,
    )

    session.add(conversation)
    session.commit()
    session.refresh(conversation)

    return conversation


def get_conversation(
    session: Session,
    conversation_id: int,
    owner_id: int,
) -> Conversation:
    statement = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.owner_id == owner_id,
    )

    conversation = session.scalar(statement)

    if conversation is None:
        raise ConversationNotFoundError(conversation_id)

    return conversation


def list_conversations(
    session: Session,
    owner_id: int,
) -> list[Conversation]:
    statement = (
        select(Conversation)
        .where(Conversation.owner_id == owner_id)
        .order_by(
            Conversation.created_at.desc(),
            Conversation.id.desc(),
        )
    )

    return list(session.scalars(statement))


def create_message(
    session: Session,
    conversation_id: int,
    owner_id: int,
    role: str,
    content: str | None,
    tool_calls: list[dict[str, object]] | None = None,
    tool_call_id: str | None = None,
) -> Message:
    get_conversation(
        session=session,
        conversation_id=conversation_id,
        owner_id=owner_id,
    )

    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        tool_calls=tool_calls,
        tool_call_id=tool_call_id,
    )

    session.add(message)
    session.commit()
    session.refresh(message)

    return message


def list_conversation_messages(
    session: Session,
    conversation_id: int,
    owner_id: int,
    limit: int = 20,
) -> list[Message]:
    get_conversation(
        session=session,
        conversation_id=conversation_id,
        owner_id=owner_id,
    )

    if limit < 1:
        raise ValueError("Message history limit must be positive")

    statement = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.id.desc())
        .limit(limit)
    )

    messages = list(session.scalars(statement))

    messages.reverse()

    return messages


def list_visible_conversation_messages(
    session: Session,
    conversation_id: int,
    owner_id: int,
    limit: int = 50,
) -> list[Message]:
    get_conversation(
        session=session,
        conversation_id=conversation_id,
        owner_id=owner_id,
    )

    if limit < 1:
        raise ValueError("Visible message limit must be positive")

    statement = (
        select(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.role.in_(
                (
                    "user",
                    "assistant",
                )
            ),
            Message.content.is_not(None),
        )
        .order_by(Message.id.desc())
        .limit(limit)
    )

    messages = list(session.scalars(statement))

    messages.reverse()

    return messages
