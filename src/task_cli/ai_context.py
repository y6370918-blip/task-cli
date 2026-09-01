import json
from typing import Any

from task_cli.models import Message

HISTORY_CANDIDATE_LIMIT = 100
MAX_HISTORY_MESSAGES = 20
MAX_HISTORY_ESTIMATED_TOKENS = 4_000

_MESSAGE_STRUCTURE_OVERHEAD = 4


def message_to_provider_data(
    message: Message,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "role": message.role,
        "content": message.content,
    }

    if message.tool_calls is not None:
        data["tool_calls"] = message.tool_calls

    if message.tool_call_id is not None:
        data["tool_call_id"] = message.tool_call_id

    return data


def estimate_message_tokens(
    message: Message,
) -> int:
    serialized = json.dumps(
        message_to_provider_data(message),
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
    )

    return len(serialized.encode("utf-8")) + _MESSAGE_STRUCTURE_OVERHEAD


def _get_tool_call_ids(
    message: Message,
) -> set[str]:
    if not message.tool_calls:
        return set()

    call_ids: set[str] = set()

    for tool_call in message.tool_calls:
        call_id = tool_call.get("id")

        if not isinstance(call_id, str):
            return set()

        if not call_id:
            return set()

        if call_id in call_ids:
            return set()

        call_ids.add(call_id)

    return call_ids


def _build_protocol_blocks(
    messages: list[Message],
) -> list[list[Message]]:
    blocks: list[list[Message]] = []

    index = 0

    while index < len(messages):
        message = messages[index]

        if message.role == "assistant" and message.tool_calls:
            expected_call_ids = _get_tool_call_ids(message)

            block = [message]
            index += 1

            while index < len(messages) and messages[index].role == "tool":
                block.append(messages[index])
                index += 1

            tool_messages = block[1:]

            actual_call_ids = {
                tool_message.tool_call_id
                for tool_message in tool_messages
                if tool_message.tool_call_id is not None
            }

            is_complete = (
                bool(expected_call_ids)
                and actual_call_ids == expected_call_ids
                and len(tool_messages) == len(expected_call_ids)
            )

            if is_complete:
                blocks.append(block)

            continue

        if message.role == "tool":
            index += 1
            continue

        if message.role in {
            "user",
            "assistant",
        }:
            blocks.append([message])

        index += 1

    return blocks


def select_history_messages(
    messages: list[Message],
    max_messages: int = (MAX_HISTORY_MESSAGES),
    max_estimated_tokens: int = (MAX_HISTORY_ESTIMATED_TOKENS),
) -> list[Message]:
    if max_messages < 1:
        raise ValueError("max_messages must be positive")

    if max_estimated_tokens < 1:
        raise ValueError("max_estimated_tokens must be positive")

    blocks = _build_protocol_blocks(messages)

    selected_blocks: list[list[Message]] = []

    selected_message_count = 0
    selected_token_count = 0

    for block in reversed(blocks):
        block_message_count = len(block)

        block_token_count = sum(estimate_message_tokens(message) for message in block)

        exceeds_message_limit = (
            selected_message_count + block_message_count > max_messages
        )

        exceeds_token_limit = (
            selected_token_count + block_token_count > max_estimated_tokens
        )

        if exceeds_message_limit or exceeds_token_limit:
            break

        selected_blocks.append(block)
        selected_message_count += block_message_count
        selected_token_count += block_token_count

    selected_messages: list[Message] = []

    for block in reversed(selected_blocks):
        selected_messages.extend(block)

    return selected_messages
