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

export type TaskCreateInput = {
  title: string;
  description: string | null;
  priority: TaskPriority;
  dueAt: string | null;
};

export type TaskUpdateInput = {
  // 当前编辑表单会提交完整的可编辑字段。
  // 后端虽然支持部分更新，但本阶段不需要构造动态 Patch 对象。
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  dueAt: string | null;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isTaskStatus(value: unknown): value is TaskStatus {
  // TypeScript 联合类型只能检查前端代码，
  // 这个函数负责检查运行时收到的网络数据。
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

function invalidTask(context: string): never {
  // context 只由前端代码提供，
  // 不包含服务器返回的任务内容。
  throw new ApiError(`${context}格式不符合预期。`);
}

function parseTask(data: unknown, context: string): TaskItem {
  if (!isRecord(data)) {
    invalidTask(context);
  }

  if (
    typeof data.id !== "number" ||
    !Number.isInteger(data.id) ||
    data.id <= 0
  ) {
    invalidTask(context);
  }

  if (typeof data.title !== "string" || data.title.length === 0) {
    invalidTask(context);
  }

  if (data.description !== null && typeof data.description !== "string") {
    invalidTask(context);
  }

  if (!isTaskStatus(data.status)) {
    invalidTask(context);
  }

  if (!isTaskPriority(data.priority)) {
    invalidTask(context);
  }

  if (data.due_at !== null && !isDateTimeString(data.due_at)) {
    invalidTask(context);
  }

  if (!isDateTimeString(data.created_at)) {
    invalidTask(context);
  }

  if (!isDateTimeString(data.updated_at)) {
    invalidTask(context);
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

  // Array.isArray 只验证了最外层是数组。
  // 每一个数组元素仍然需要单独验证。
  const items: unknown[] = data;

  return items.map((item, index) =>
    parseTask(item, `任务列表第 ${index + 1} 项`),
  );
}

function getAuthorization(accessToken: string): string {
  const token = accessToken.trim();

  if (token === "") {
    throw new ApiError("缺少登录凭证。");
  }

  // 集中构造认证请求头，
  // 避免多个 API 函数重复拼接 Bearer Token。
  return `Bearer ${token}`;
}

function validateTaskId(taskId: number): void {
  // 虽然后端还会检查任务是否存在，
  // 前端仍应拒绝明显不合法的 ID。
  if (!Number.isInteger(taskId) || taskId <= 0) {
    throw new ApiError("任务 ID 不合法。");
  }
}

export async function listTasks(
  accessToken: string,
  filters: TaskFilters,
): Promise<TaskItem[]> {
  const query = new URLSearchParams();

  // Day54 暂未实现分页控件，
  // 先请求后端允许的最大数量。
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
      // owner_id 不由前端提供。
      // 后端从经过验证的 Token 中确定当前用户。
      Authorization: getAuthorization(accessToken),
    },
  });

  return parseTaskList(data);
}

export async function createTask(
  accessToken: string,
  input: TaskCreateInput,
): Promise<TaskItem> {
  const data = await apiRequest<unknown>("/tasks/", {
    method: "POST",
    headers: {
      Authorization: getAuthorization(accessToken),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      title: input.title,
      description: input.description,
      priority: input.priority,

      // 前端使用 camelCase，
      // 发送给 FastAPI 时转换成 snake_case。
      due_at: input.dueAt,
    }),
  });

  // 创建和修改都复用与任务列表相同的
  // 运行时响应字段验证。
  return parseTask(data, "创建任务响应");
}

export async function updateTask(
  accessToken: string,
  taskId: number,
  input: TaskUpdateInput,
): Promise<TaskItem> {
  validateTaskId(taskId);

  const data = await apiRequest<unknown>(`/tasks/${taskId}`, {
    method: "PUT",
    headers: {
      Authorization: getAuthorization(accessToken),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      title: input.title,
      description: input.description,
      status: input.status,
      priority: input.priority,

      // null 会明确要求后端清除截止时间。
      // 它与“不发送 due_at”具有不同含义。
      due_at: input.dueAt,
    }),
  });

  return parseTask(data, "更新任务响应");
}

export async function deleteTask(
  accessToken: string,
  taskId: number,
): Promise<void> {
  validateTaskId(taskId);

  const data = await apiRequest<unknown>(`/tasks/${taskId}`, {
    method: "DELETE",
    headers: {
      Authorization: getAuthorization(accessToken),
    },
  });

  // 当前真实 REST 接口返回：
  // {"message": "Task deleted"}
  //
  // 删除属于写操作，不能只看到 HTTP 200
  // 就完全忽略后端响应协议。
  if (!isRecord(data) || data.message !== "Task deleted") {
    throw new ApiError("删除任务响应格式不符合预期。");
  }
}
