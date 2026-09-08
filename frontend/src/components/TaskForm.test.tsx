import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import type { TaskItem, TaskUpdateInput } from "../api/tasks";
import { TaskForm } from "./TaskForm";

// 每次调用都返回一个新的测试对象。
// 使用固定日期，不依赖测试执行当天。
function makeTask(): TaskItem {
  return {
    id: 6,
    title: "原始任务",
    description: "原始描述",
    status: "pending",
    priority: "medium",

    // 故意包含六位小数秒和明确的时区偏移。
    // 如果表单无意中重新转换时间，可能丢失精度。
    dueAt: "2026-09-07T15:00:00.123456+08:00",

    createdAt: "2026-09-01T08:00:00Z",
    updatedAt: "2026-09-01T08:00:00Z",
  };
}

describe("TaskForm 编辑模式", () => {
  test("只修改标题时，完整保留原始截止时间", async () => {
    const task = makeTask();

    // 类型参数表示：
    // 接收 TaskUpdateInput，返回 Promise<void>。
    // 模拟父组件提供的提交函数，不调用后端。
    const onSubmit = vi
      .fn<(input: TaskUpdateInput) => Promise<void>>()
      .mockResolvedValue(undefined);

    // render 会真正挂载 TaskForm。
    // useState、onChange 和 onSubmit 都使用业务组件的真实实现。
    render(
      <TaskForm
        mode="edit"
        task={task}
        submitting={false}
        onSubmit={onSubmit}
        onCancel={vi.fn()}
      />,
    );

    // 按标签查找输入框，而不是依赖 CSS 类名。
    // 这也要求 label 与 input 正确关联。
    fireEvent.change(screen.getByLabelText("标题"), {
      target: { value: "修改后的任务" },
    });

    fireEvent.click(screen.getByRole("button", { name: "保存修改" }));

    // waitFor 会重试内部断言，直到通过或超时。
    // 这里只等待结果，不要把点击操作放进 waitFor，
    // 否则重试可能重复点击。
    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledTimes(1);
    });

    expect(onSubmit).toHaveBeenCalledWith({
      title: "修改后的任务",
      description: "原始描述",
      status: "pending",
      priority: "medium",

      // 检查原字符串，而不只是两个时间是否大致相等。
      dueAt: task.dueAt,
    });
  });

  test("清空截止时间后提交 null", async () => {
    const task = makeTask();
    const onSubmit = vi
      .fn<(input: TaskUpdateInput) => Promise<void>>()
      .mockResolvedValue(undefined);

    render(
      <TaskForm
        mode="edit"
        task={task}
        submitting={false}
        onSubmit={onSubmit}
        onCancel={vi.fn()}
      />,
    );

    // 触发真实 onChange，让 React state 变为空字符串。
    fireEvent.change(screen.getByLabelText("截止时间"), {
      target: { value: "" },
    });

    fireEvent.click(screen.getByRole("button", { name: "保存修改" }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledTimes(1);
    });

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        // 空输入必须转换为 null，而不是字符串 "null"。
        dueAt: null,
      }),
    );
  });

  test("submitting 为 true 时禁用按钮并拒绝提交", () => {
    const onSubmit = vi
      .fn<(input: TaskUpdateInput) => Promise<void>>()
      .mockResolvedValue(undefined);

    render(
      <TaskForm
        mode="edit"
        task={makeTask()}
        submitting={true}
        onSubmit={onSubmit}
        onCancel={vi.fn()}
      />,
    );

    const button = screen.getByRole("button", {
      name: "保存中……",
    });

    // 当前没有安装 jest-dom，
    // 使用原生 DOM 方法检查 disabled 属性即可。
    expect(button.hasAttribute("disabled")).toBe(true);

    fireEvent.click(button);
    expect(onSubmit).not.toHaveBeenCalled();

    // 再直接触发表单提交事件，验证 handleSubmit 内的保护。
    // 这是定向测试防御分支，不是在模拟正常用户绕过按钮。
    const form = button.closest("form");

    if (form === null) {
      throw new Error("保存按钮没有位于表单内");
    }

    fireEvent.submit(form);
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
