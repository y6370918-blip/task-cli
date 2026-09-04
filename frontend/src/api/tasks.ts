import { ApiError, apiRequest } from "./client";

export type TaskStatus = "pending" | "doing" | "done";

export type TaskPriority = "low" | "medium" | "high";

export type TaskItem = {
  id: number;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  dueAt: string | null;
  createdAt: string;
  updatedAt: string;
};

export type TaskFilters = {
  // 空字符串表示“全部”，请求时不会把它发送给后端。
  status: TaskStatus | "";
  priority: TaskPriority | "";
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isTaskStatus(value: unknown): value is TaskStatus {
  // 这个运行时检查与上面的 TypeScript 联合类型对应。
  // 联合类型检查前端代码，函数检查网络响应。
  return value === "pending" || value === "doing" || value === "done";
}

function isTaskPriority(value: unknown): value is TaskPriority {
  return value === "low" || value === "medium" || value === "high";
}

function isDateTimeString(value: unknown): value is string {
  if (typeof value !== "string") {
    return false;
  }

  // 当前后端 datetime 会序列化成包含日期和 T 的字符串。
  // created_at 目前可能不包含时区，因此这里不强制要求 Z 或偏移量。
  const looksLikeIsoDateTime = /^\d{4}-\d{2}-\d{2}T/.test(value);

  return looksLikeIsoDateTime && !Number.isNaN(Date.parse(value));
}

function invalidTask(index: number): never {
  // 不把完整响应写进错误消息，避免意外暴露任务内容。
  throw new ApiError(`任务列表第 ${index + 1} 项格式不符合预期。`);
}

function parseTask(data: unknown, index: number): TaskItem {
  if (!isRecord(data)) {
    invalidTask(index);
  }

  if (
    typeof data.id !== "number" ||
    !Number.isInteger(data.id) ||
    data.id <= 0
  ) {
    invalidTask(index);
  }

  if (typeof data.title !== "string" || data.title.length === 0) {
    invalidTask(index);
  }

  if (data.description !== null && typeof data.description !== "string") {
    invalidTask(index);
  }

  if (!isTaskStatus(data.status)) {
    invalidTask(index);
  }

  if (!isTaskPriority(data.priority)) {
    invalidTask(index);
  }

  if (data.due_at !== null && !isDateTimeString(data.due_at)) {
    invalidTask(index);
  }

  if (!isDateTimeString(data.created_at)) {
    invalidTask(index);
  }

  if (!isDateTimeString(data.updated_at)) {
    invalidTask(index);
  }

  // 后端字段使用 snake_case，
  // 前端对象统一转换成 camelCase。
  return {
    id: data.id,
    title: data.title,
    description: data.description,
    status: data.status,
    priority: data.priority,
    dueAt: data.due_at,
    createdAt: data.created_at,
    updatedAt: data.updated_at,
  };
}

function parseTaskList(data: unknown): TaskItem[] {
  if (!Array.isArray(data)) {
    throw new ApiError("任务列表响应格式不符合预期。");
  }

  // Array.isArray 只验证外层。
  // 将元素重新视为 unknown，逐项交给 parseTask 验证。
  const items: unknown[] = data;

  return items.map((item, index) => parseTask(item, index));
}

export async function listTasks(
  accessToken: string,
  filters: TaskFilters,
): Promise<TaskItem[]> {
  if (accessToken.trim() === "") {
    throw new ApiError("缺少登录凭证。");
  }

  const query = new URLSearchParams();

  // Day54 暂不实现分页控件，先请求后端允许的最大数量。
  // 页面稍后会明确提示“最多显示 100 条”。
  query.set("limit", "100");

  if (filters.status !== "") {
    query.set("status", filters.status);
  }

  if (filters.priority !== "") {
    query.set("priority", filters.priority);
  }

  const data = await apiRequest<unknown>(`/tasks/?${query.toString()}`, {
    method: "GET",
    headers: {
      // owner_id 不出现在请求中。
      // 后端从经过验证的 Token 中确定当前用户。
      Authorization: `Bearer ${accessToken}`,
    },
  });

  return parseTaskList(data);
}
