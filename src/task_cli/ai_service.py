import json
import logging
from typing import Any

from sqlalchemy.orm import Session

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
- 删除属于危险操作，只能请求删除，不能直接执行删除。
"""


def run_task_assistant(
    db: Session,
    owner_id: int,
    message: str,
) -> str:

    messages: list[Any] = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": message,
        },
    ]

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
                "AI provider failed owner_id=%s error_type=%s",
                owner_id,
                type(exc).__name__,
            )

            raise

            raise

        assistant_message = response.choices[0].message

        tool_calls = assistant_message.tool_calls

        if not tool_calls:
            return assistant_message.content or "AI 没有返回有效内容。"

        messages.append(
            {
                "role": "assistant",
                "content": (assistant_message.content),
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": (call.function.name),
                            "arguments": (call.function.arguments),
                        },
                    }
                    for call in tool_calls
                ],
            }
        )

        # =================================================
        # 5. 执行所有 Tool Calls
        # =================================================

        for call in tool_calls:
            tool_name = call.function.name

            logger.info(
                "AI tool call name=%s owner_id=%s",
                tool_name,
                owner_id,
            )

            # ---------------------------------------------
            # 解析 DeepSeek 返回的 JSON 参数
            # ---------------------------------------------

            try:
                arguments = json.loads(call.function.arguments)

            except json.JSONDecodeError:
                logger.warning(
                    "AI tool arguments invalid name=%s owner_id=%s",
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

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": tool_result,
                    }
                )

                continue

            # =================================================
            # 6. 构造工具调用唯一标识
            #
            # 例如：
            #
            # update_task:
            # {"status":"done","task_id":2}
            # =================================================

            normalized_arguments = json.dumps(
                arguments,
                ensure_ascii=False,
                sort_keys=True,
            )

            call_key = f"{tool_name}:{normalized_arguments}"

            # =================================================
            # 7. 防止重复执行完全相同的工具
            # =================================================

            if call_key in executed_calls:
                logger.warning(
                    "Duplicate AI tool call prevented name=%s owner_id=%s",
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

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": tool_result,
                    }
                )

                continue

            # 在真正执行之前记录
            executed_calls.add(call_key)

            # =================================================
            # 8. 真正执行 Python Tool
            # =================================================

            try:
                tool_result = execute_tool(
                    name=tool_name,
                    arguments=arguments,
                    db=db,
                    owner_id=owner_id,
                )

            except AIToolError as exc:
                logger.warning(
                    "AI tool failed name=%s owner_id=%s error=%s",
                    tool_name,
                    owner_id,
                    exc,
                )

                tool_result = json.dumps(
                    {
                        "success": False,
                        "error": str(exc),
                    },
                    ensure_ascii=False,
                )

            # =================================================
            # 9. 把 Tool Result 加回消息历史
            # =================================================

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": tool_result,
                }
            )

            # =================================================
            # 10. 尝试读取 Tool Result
            # =================================================

            try:
                result_data = json.loads(tool_result)

            except json.JSONDecodeError:
                result_data = {}

            # =================================================
            # 11. 如果工具执行失败
            #
            # 不直接退出。
            #
            # 让 DeepSeek 下一轮根据错误给用户解释。
            # =================================================

            if not result_data.get(
                "success",
                False,
            ):
                continue

            # =================================================
            # 12. 创建成功
            #
            # 写操作已经完成。
            #
            # Python 直接返回，
            # 不再让 DeepSeek重复决定是否 create。
            # =================================================

            if tool_name == "create_task":
                task = result_data.get(
                    "task",
                    {},
                )
                due_at = task.get("due_at") or "未设置"

                return (
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

            # =================================================
            # 13. 修改成功
            #
            # 这是你当前死循环问题的关键修复。
            # =================================================

            if tool_name == "update_task":
                task = result_data.get(
                    "task",
                    {},
                )
                due_at = task.get("due_at") or "未设置"

                return (
                    f"任务 #{task.get('id')} "
                    f"已修改成功。"
                    f"当前状态为 "
                    f"{task.get('status')}，"
                    f"优先级为 "
                    f"{task.get('priority')}。"
                    f"截止时间为 "
                    f"{due_at}。"
                )

            # =================================================
            # 14. 请求删除
            #
            # 不执行真正 DELETE。
            # =================================================

            if tool_name == "request_delete_task":
                task_id = result_data.get("task_id")

                confirmation_id = result_data.get("confirmation_id")

                return (
                    f"删除任务 #{task_id} "
                    f"需要确认。"
                    f"确认操作编号为 "
                    f"#{confirmation_id}。"
                    f"请确认或取消该操作。"
                )

            # =================================================
            # list_tasks 不在这里 return
            #
            # 因为我们希望 DeepSeek 根据真实任务数据，
            # 给用户整理成自然语言回答。
            #
            # 所以继续下一轮。
            # =================================================

    # =====================================================
    # 5轮之后仍然没有结束
    # =====================================================

    logger.warning(
        "AI agent exceeded max rounds owner_id=%s",
        owner_id,
    )

    return "AI 执行步骤过多，请尝试把请求描述得更简单一些。"
