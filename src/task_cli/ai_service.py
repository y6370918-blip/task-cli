import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from task_cli.ai_context import (
    HISTORY_CANDIDATE_LIMIT,
    message_to_provider_data,
    select_history_messages,
)
from task_cli.ai_exceptions import (
    AIProviderError,
    AIToolError,
)
from task_cli.ai_provider import (
    call_ai_provider,
)
from task_cli.ai_tools import (
    execute_tool,
)
from task_cli.conversation_service import (
    create_message,
    list_conversation_messages,
)
from task_cli.schemas_ai import (
    AssistantResult,
    PendingActionRead,
)

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """
你是 task-cli 的 AI 任务助手。

你可以帮助当前登录用户：
1. 查看自己的任务；
2. 创建自己的任务；
3. 修改自己的任务；
4. 请求删除自己的任务；
5. 总结自己的任务；
6. 根据已有任务给出简单建议。

规则：
- 当需要读取、创建或修改真实任务数据时，必须使用提供的工具。
- 工具已经成功返回结果后，不要为了确认结果而重复执行相同工具。
- 只有确实需要新的数据库操作时，才能再次调用工具。
- 不要假装已经执行了实际上没有执行的数据库操作。
- 只能操作当前登录用户自己的任务。
- 不要要求用户提供 owner_id。
- owner_id 由系统根据当前登录用户决定。
- 不要猜测数据库中的任务内容。
- 设置或修改截止时间时，只能使用包含时区的明确日期时间。
- 如果用户只提供相对或模糊时间，必须先要求用户补充明确日期和时区，不能猜测后调用工具。
- 用户明确要求清除截止时间时，调用 update_task 并把 due_at 设为 null。
- 用户明确要求删除任务且目标 task_id 已明确时，调用 request_delete_task。
- 不要先进行额外的口头确认。
- request_delete_task 只创建待确认操作，不会真正删除任务。
- AI 删除流程的实际执行由用户点击页面确认按钮触发，不能用聊天中的“确认”代替按钮操作。
- 如果目标任务不明确，先查询任务或追问用户，不得猜测 task_id。
- 待确认操作编号必须来自工具返回结果，不得自行编造。
"""


def _persist_message(
    db: Session,
    owner_id: int,
    conversation_id: int | None,
    role: str,
    content: str | None,
    tool_calls: (list[dict[str, object]] | None) = None,
    tool_call_id: str | None = None,
) -> None:
    if conversation_id is None:
        return

    create_message(
        session=db,
        conversation_id=conversation_id,
        owner_id=owner_id,
        role=role,
        content=content,
        tool_calls=tool_calls,
        tool_call_id=tool_call_id,
    )


def _append_tool_message(
    messages: list[Any],
    db: Session,
    owner_id: int,
    conversation_id: int | None,
    tool_call_id: str,
    content: str,
) -> None:
    messages.append(
        {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content,
        }
    )

    _persist_message(
        db=db,
        owner_id=owner_id,
        conversation_id=conversation_id,
        role="tool",
        content=content,
        tool_call_id=tool_call_id,
    )


def _finish_with_assistant_reply(
    db: Session,
    owner_id: int,
    conversation_id: int | None,
    reply: str,
    pending_action: PendingActionRead | None = None,
) -> AssistantResult:
    # 消息表仍然保存回复文字。
    # PendingAction 本身已由工具保存到数据库，
    # 这里不重复创建待确认操作。
    _persist_message(
        db=db,
        owner_id=owner_id,
        conversation_id=conversation_id,
        role="assistant",
        content=reply,
    )

    # 所有返回分支都获得相同形状的结果。
    # 普通回复不传 pending_action，自动使用 None。
    return AssistantResult(
        reply=reply,
        pending_action=pending_action,
    )


def run_task_assistant_result(
    db: Session,
    owner_id: int,
    message: str,
    conversation_id: int | None = None,
) -> AssistantResult:
    messages: list[Any] = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
    ]

    if conversation_id is not None:
        candidates = list_conversation_messages(
            session=db,
            conversation_id=conversation_id,
            owner_id=owner_id,
            limit=(HISTORY_CANDIDATE_LIMIT),
        )

        history = select_history_messages(candidates)

        messages.extend(
            message_to_provider_data(history_message) for history_message in history
        )

    messages.append(
        {
            "role": "user",
            "content": message,
        }
    )

    _persist_message(
        db=db,
        owner_id=owner_id,
        conversation_id=conversation_id,
        role="user",
        content=message,
    )

    executed_calls: set[str] = set()

    for round_number in range(5):
        logger.info(
            "AI agent round=%s owner_id=%s",
            round_number + 1,
            owner_id,
        )

        try:
            response = call_ai_provider(messages)

        except AIProviderError as exc:
            logger.error(
                ("AI provider failed owner_id=%s error_type=%s"),
                owner_id,
                type(exc).__name__,
            )

            raise

        assistant_message = response.choices[0].message

        tool_calls = assistant_message.tool_calls

        if not tool_calls:
            reply = assistant_message.content or "AI 没有返回有效内容。"

            return _finish_with_assistant_reply(
                db=db,
                owner_id=owner_id,
                conversation_id=(conversation_id),
                reply=reply,
            )

        serialized_tool_calls: list[dict[str, object]] = [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": (call.function.name),
                    "arguments": (call.function.arguments),
                },
            }
            for call in tool_calls
        ]

        messages.append(
            {
                "role": "assistant",
                "content": (assistant_message.content),
                "tool_calls": (serialized_tool_calls),
            }
        )

        _persist_message(
            db=db,
            owner_id=owner_id,
            conversation_id=conversation_id,
            role="assistant",
            content=(assistant_message.content),
            tool_calls=serialized_tool_calls,
        )

        # 执行本轮的所有 Tool Calls。
        for call in tool_calls:
            tool_name = call.function.name

            logger.info(
                ("AI tool call name=%s owner_id=%s"),
                tool_name,
                owner_id,
            )

            try:
                arguments = json.loads(call.function.arguments)

            except json.JSONDecodeError:
                logger.warning(
                    ("AI tool arguments invalid name=%s owner_id=%s"),
                    tool_name,
                    owner_id,
                )

                tool_result = json.dumps(
                    {
                        "success": False,
                        "error": ("工具参数不是有效的 JSON。"),
                    },
                    ensure_ascii=False,
                )

                _append_tool_message(
                    messages=messages,
                    db=db,
                    owner_id=owner_id,
                    conversation_id=(conversation_id),
                    tool_call_id=call.id,
                    content=tool_result,
                )

                continue

            normalized_arguments = json.dumps(
                arguments,
                ensure_ascii=False,
                sort_keys=True,
            )

            call_key = f"{tool_name}:{normalized_arguments}"

            if call_key in executed_calls:
                logger.warning(
                    ("Duplicate AI tool call prevented name=%s owner_id=%s"),
                    tool_name,
                    owner_id,
                )

                tool_result = json.dumps(
                    {
                        "success": False,
                        "error": ("这个完全相同的工具调用已经执行过，不要再次执行。"),
                    },
                    ensure_ascii=False,
                )

                _append_tool_message(
                    messages=messages,
                    db=db,
                    owner_id=owner_id,
                    conversation_id=(conversation_id),
                    tool_call_id=call.id,
                    content=tool_result,
                )

                continue

            executed_calls.add(call_key)

            try:
                tool_result = execute_tool(
                    name=tool_name,
                    arguments=arguments,
                    db=db,
                    owner_id=owner_id,
                )

            except AIToolError as exc:
                logger.warning(
                    "AI tool failed name=%s owner_id=%s error_type=%s",
                    tool_name,
                    owner_id,
                    type(exc).__name__,
                )

                tool_result = json.dumps(
                    {
                        "success": False,
                        "error": str(exc),
                    },
                    ensure_ascii=False,
                )

            _append_tool_message(
                messages=messages,
                db=db,
                owner_id=owner_id,
                conversation_id=(conversation_id),
                tool_call_id=call.id,
                content=tool_result,
            )

            try:
                result_data = json.loads(tool_result)

            except json.JSONDecodeError:
                result_data = {}

            if not result_data.get(
                "success",
                False,
            ):
                continue

            # 写操作成功后直接返回，防止模型重复执行。
            if tool_name == "create_task":
                task = result_data.get(
                    "task",
                    {},
                )

                due_at = task.get("due_at") or "未设置"

                reply = (
                    f"任务已创建："
                    f"#{task.get('id')} "
                    f"{task.get('title')}，"
                    f"当前状态为 "
                    f"{task.get('status')}，"
                    f"优先级为 "
                    f"{task.get('priority')}。"
                    f"截止时间为 "
                    f"{due_at}。"
                )

                return _finish_with_assistant_reply(
                    db=db,
                    owner_id=owner_id,
                    conversation_id=(conversation_id),
                    reply=reply,
                )

            if tool_name == "update_task":
                task = result_data.get(
                    "task",
                    {},
                )

                due_at = task.get("due_at") or "未设置"

                reply = (
                    f"任务 #{task.get('id')} "
                    f"已修改成功。"
                    f"当前状态为 "
                    f"{task.get('status')}，"
                    f"优先级为 "
                    f"{task.get('priority')}。"
                    f"截止时间为 "
                    f"{due_at}。"
                )

                return _finish_with_assistant_reply(
                    db=db,
                    owner_id=owner_id,
                    conversation_id=(conversation_id),
                    reply=reply,
                )

            if tool_name == "request_delete_task":
                # 从真实 Python 工具的结构化结果构造对象。
                # confirmation_id 是工具现有字段；
                # action_id 是提供给 Router 和前端的字段。
                pending_action = PendingActionRead.model_validate(
                    {
                        "action_id": result_data.get("confirmation_id"),
                        "action": result_data.get("action"),
                        "task_id": result_data.get("task_id"),
                        "expires_at": result_data.get("expires_at"),
                    }
                )

                # 展示文字使用已经验证的字段生成。
                # 前端之后直接读取 pending_action，
                # 不需要从这段中文中提取编号。
                reply = (
                    f"删除任务 #{pending_action.task_id} "
                    f"需要确认。"
                    f"确认操作编号为 "
                    f"#{pending_action.action_id}。"
                    f"请确认或取消该操作。"
                )

                return _finish_with_assistant_reply(
                    db=db,
                    owner_id=owner_id,
                    conversation_id=conversation_id,
                    reply=reply,
                    pending_action=pending_action,
                )

            # list_tasks 是读操作，需要模型继续整理结果。

    logger.warning(
        ("AI agent exceeded max rounds owner_id=%s"),
        owner_id,
    )

    reply = "AI 执行步骤过多，请尝试把请求描述得更简单一些。"

    return _finish_with_assistant_reply(
        db=db,
        owner_id=owner_id,
        conversation_id=conversation_id,
        reply=reply,
    )


def run_task_assistant(
    db: Session,
    owner_id: int,
    message: str,
    conversation_id: int | None = None,
) -> str:
    # 保留旧入口的字符串返回约定。
    # Agent 只执行一次，这里仅取出结果对象中的 reply。
    result = run_task_assistant_result(
        db=db,
        owner_id=owner_id,
        message=message,
        conversation_id=conversation_id,
    )

    return result.reply
