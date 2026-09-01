from task_cli.ai_context import (
    estimate_message_tokens,
    select_history_messages,
)
from task_cli.models import Message


def make_message(
    role: str,
    content: str | None,
    tool_calls: (list[dict[str, object]] | None) = None,
    tool_call_id: str | None = None,
) -> Message:
    return Message(
        conversation_id=1,
        role=role,
        content=content,
        tool_calls=tool_calls,
        tool_call_id=tool_call_id,
    )


def test_select_history_keeps_multiple_tool_calls_together() -> None:
    assistant_call = make_message(
        role="assistant",
        content=None,
        tool_calls=[
            {
                "id": "call-1",
                "type": "function",
            },
            {
                "id": "call-2",
                "type": "function",
            },
        ],
    )

    first_result = make_message(
        role="tool",
        content='{"success": true}',
        tool_call_id="call-1",
    )

    second_result = make_message(
        role="tool",
        content='{"success": true}',
        tool_call_id="call-2",
    )

    final_reply = make_message(
        role="assistant",
        content="两个工具都已执行。",
    )

    selected = select_history_messages(
        [
            assistant_call,
            first_result,
            second_result,
            final_reply,
        ],
        max_messages=4,
        max_estimated_tokens=100_000,
    )

    assert selected == [
        assistant_call,
        first_result,
        second_result,
        final_reply,
    ]


def test_select_history_does_not_split_tool_block() -> None:
    assistant_call = make_message(
        role="assistant",
        content=None,
        tool_calls=[
            {
                "id": "call-1",
                "type": "function",
            },
            {
                "id": "call-2",
                "type": "function",
            },
        ],
    )

    first_result = make_message(
        role="tool",
        content="第一个结果",
        tool_call_id="call-1",
    )

    second_result = make_message(
        role="tool",
        content="第二个结果",
        tool_call_id="call-2",
    )

    final_reply = make_message(
        role="assistant",
        content="最终回复",
    )

    selected = select_history_messages(
        [
            assistant_call,
            first_result,
            second_result,
            final_reply,
        ],
        max_messages=3,
        max_estimated_tokens=100_000,
    )

    assert selected == [
        final_reply,
    ]


def test_select_history_drops_orphan_tool_message() -> None:
    orphan_tool = make_message(
        role="tool",
        content="找不到对应 Tool Call",
        tool_call_id="missing-call",
    )

    final_reply = make_message(
        role="assistant",
        content="正常回复",
    )

    selected = select_history_messages(
        [
            orphan_tool,
            final_reply,
        ],
        max_messages=20,
        max_estimated_tokens=100_000,
    )

    assert selected == [
        final_reply,
    ]


def test_select_history_drops_incomplete_tool_block() -> None:
    incomplete_call = make_message(
        role="assistant",
        content=None,
        tool_calls=[
            {
                "id": "call-without-result",
                "type": "function",
            },
        ],
    )

    final_reply = make_message(
        role="assistant",
        content="稍后重新尝试。",
    )

    selected = select_history_messages(
        [
            incomplete_call,
            final_reply,
        ],
        max_messages=20,
        max_estimated_tokens=100_000,
    )

    assert selected == [
        final_reply,
    ]


def test_select_history_stops_at_token_budget() -> None:
    older_message = make_message(
        role="user",
        content="较早的消息",
    )

    recent_message = make_message(
        role="assistant",
        content="最新回复",
    )

    recent_message_budget = estimate_message_tokens(recent_message)

    selected = select_history_messages(
        [
            older_message,
            recent_message,
        ],
        max_messages=20,
        max_estimated_tokens=(recent_message_budget),
    )

    assert selected == [
        recent_message,
    ]
