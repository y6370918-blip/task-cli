import { ApiError, apiRequest } from "./client";

export type PendingActionItem = {
  actionId: number;
  action: "delete_task";
  taskId: number;
  expiresAt: string;
};

export type AssistantInput = {
  message: string;

  // 首次请求使用 null。
  // 后续请求使用上一次响应中的 conversationId。
  conversationId: number | null;
};

export type AssistantReply = {
  conversationId: number;
  reply: string;
  pendingAction: PendingActionItem | null;
};

export type AssistantActionResult = {
  actionId: number;
  status: "confirmed" | "cancelled";
  message: string;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  // JSON 对象与数组都属于 object，
  // 因此这里同时排除 null 和数组。
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isPositiveId(value: unknown): value is number {
  // SafeInteger 同时检查整数和 JavaScript 能准确表示的范围。
  return typeof value === "number" && Number.isSafeInteger(value) && value > 0;
}

function isAwareDateTime(value: unknown): value is string {
  if (typeof value !== "string") {
    return false;
  }

  // 对应当前后端输出的时间格式：
  // 2026-09-05T12:30:00Z
  // 2026-09-05T20:30:00+08:00
  // 秒之后可以带小数，但末尾必须有时区。
  const pattern =
    /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/;

  return pattern.test(value) && !Number.isNaN(Date.parse(value));
}

function getAuthorization(accessToken: string): string {
  const token = accessToken.trim();

  if (token === "") {
    throw new ApiError("缺少登录凭证。");
  }

  return `Bearer ${token}`;
}

function parsePendingAction(data: unknown): PendingActionItem | null {
  if (data === null) {
    return null;
  }

  if (
    !isRecord(data) ||
    !isPositiveId(data.action_id) ||
    data.action !== "delete_task" ||
    !isPositiveId(data.task_id) ||
    !isAwareDateTime(data.expires_at)
  ) {
    throw new ApiError("待确认操作响应格式不符合预期。");
  }

  // 只读取正式协议字段，不从 reply 文本中提取编号。
  // 后端 snake_case 在这里转换成前端 camelCase。
  return {
    actionId: data.action_id,
    action: data.action,
    taskId: data.task_id,
    expiresAt: data.expires_at,
  };
}

function parseAssistantReply(data: unknown): AssistantReply {
  if (
    !isRecord(data) ||
    !isPositiveId(data.conversation_id) ||
    typeof data.reply !== "string"
  ) {
    throw new ApiError("AI 助手响应格式不符合预期。");
  }

  return {
    conversationId: data.conversation_id,
    reply: data.reply,

    // 缺少字段时，undefined 会被验证函数拒绝。
    // 不使用 ?? null，否则可能把旧后端缺少字段的问题隐藏起来。
    pendingAction: parsePendingAction(data.pending_action),
  };
}

export async function sendAssistantMessage(
  accessToken: string,
  input: AssistantInput,
): Promise<AssistantReply> {
  const message = input.message.trim();

  if (message === "") {
    throw new ApiError("消息不能为空。");
  }

  // Array.from 按 Unicode 码点计数。
  // 例如某些 emoji 的 string.length 是 2，
  // 而后端 Python 通常将这个字符计为 1。
  if (Array.from(message).length > 1000) {
    throw new ApiError("消息不能超过 1000 个字符。");
  }

  if (input.conversationId !== null && !isPositiveId(input.conversationId)) {
    throw new ApiError("会话 ID 不合法。");
  }

  // Assistant 请求可能执行数据库写操作。
  // 没收到成功响应，并不证明服务器没有执行，
  // 所以这里不添加自动重试。
  const data = await apiRequest<unknown>("/assistant/", {
    method: "POST",
    headers: {
      Authorization: getAuthorization(accessToken),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message,

      // null 会让后端创建新会话。
      // 用户身份仍由 Authorization 中的 JWT 确定。
      conversation_id: input.conversationId,
    }),
  });

  const result = parseAssistantReply(data);

  if (
    input.conversationId !== null &&
    result.conversationId !== input.conversationId
  ) {
    // 继续某个会话时，响应必须仍属于这个会话，
    // 避免前端把回复追加到错误的对话中。
    throw new ApiError("AI 助手返回的会话 ID 与请求不一致。");
  }

  return result;
}

async function submitActionDecision(
  accessToken: string,
  actionId: number,
  decision: "confirm" | "cancel",
): Promise<AssistantActionResult> {
  if (!isPositiveId(actionId)) {
    throw new ApiError("待确认操作 ID 不合法。");
  }

  const data = await apiRequest<unknown>(
    `/assistant/actions/${actionId}/${decision}`,
    {
      method: "POST",
      headers: {
        Authorization: getAuthorization(accessToken),
      },

      // 真实接口从 URL 获取 action_id，
      // 从 JWT 获取当前用户，因此不需要 JSON 请求体。
      // 所有权、状态和过期时间仍由后端检查。
    },
  );

  const expectedStatus = decision === "confirm" ? "confirmed" : "cancelled";

  if (
    !isRecord(data) ||
    !isPositiveId(data.action_id) ||
    data.action_id !== actionId ||
    data.status !== expectedStatus ||
    typeof data.message !== "string"
  ) {
    // 确认请求应返回 confirmed，
    // 取消请求应返回 cancelled，
    // 而且必须对应本次请求的操作编号。
    throw new ApiError("操作处理响应格式不符合预期。");
  }

  return {
    actionId: data.action_id,
    status: expectedStatus,
    message: data.message,
  };
}

export async function confirmAssistantAction(
  accessToken: string,
  actionId: number,
): Promise<AssistantActionResult> {
  return submitActionDecision(accessToken, actionId, "confirm");
}

export async function cancelAssistantAction(
  accessToken: string,
  actionId: number,
): Promise<AssistantActionResult> {
  return submitActionDecision(accessToken, actionId, "cancel");
}

export type ConversationItem = {
  id: number;

  // JSON 中的时间是字符串，不是 JavaScript Date 对象。
  createdAt: string;
};

export type ConversationMessageItem = {
  id: number;

  // 对应历史展示接口，不接收 system 或 tool 消息。
  role: "user" | "assistant";

  content: string;
  createdAt: string;
};

function isConversationDateTime(value: unknown): value is string {
  if (typeof value !== "string") {
    return false;
  }

  // 当前会话 Schema 使用 datetime，而不是 AwareDatetime。
  // 允许带时区或不带时区的 ISO 日期时间。
  // 保留原文，不擅自补时区。
  //
  // 这里做基本格式和可解析性检查，不转换存储值。
  const pattern =
    /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?$/;

  return pattern.test(value) && !Number.isNaN(Date.parse(value));
}

function parseConversation(data: unknown): ConversationItem {
  if (
    !isRecord(data) ||
    !isPositiveId(data.id) ||
    !isConversationDateTime(data.created_at)
  ) {
    throw new ApiError("会话列表中的数据格式不符合预期。");
  }

  // 只提取需要的字段，统一前端的 camelCase 命名。
  return {
    id: data.id,
    createdAt: data.created_at,
  };
}

function parseConversationMessage(data: unknown): ConversationMessageItem {
  if (
    !isRecord(data) ||
    !isPositiveId(data.id) ||
    (data.role !== "user" && data.role !== "assistant") ||
    typeof data.content !== "string" ||
    !isConversationDateTime(data.created_at)
  ) {
    throw new ApiError("历史消息的数据格式不符合预期。");
  }

  // 历史文字仅用于展示，不从 content 中提取操作编号。
  return {
    id: data.id,
    role: data.role,
    content: data.content,
    createdAt: data.created_at,
  };
}

export async function listAssistantConversations(
  accessToken: string,
): Promise<ConversationItem[]> {
  // 用户身份由 JWT 确定，不传 owner_id。
  const data = await apiRequest<unknown>("/assistant/conversations", {
    method: "GET",
    headers: {
      Authorization: getAuthorization(accessToken),
    },
  });

  if (!Array.isArray(data)) {
    throw new ApiError("会话列表响应不是数组。");
  }

  // 外层是数组还不够，每一项都必须通过校验。
  // 保留后端按创建时间倒序排列的结果。
  return data.map((item: unknown) => parseConversation(item));
}

export async function getAssistantConversationMessages(
  accessToken: string,
  conversationId: number,
): Promise<ConversationMessageItem[]> {
  if (!isPositiveId(conversationId)) {
    throw new ApiError("会话 ID 不合法。");
  }

  // 前端检查编号格式。
  // 后端仍要检查会话是否属于当前用户。
  const data = await apiRequest<unknown>(
    `/assistant/conversations/${conversationId}/messages`,
    {
      method: "GET",
      headers: {
        Authorization: getAuthorization(accessToken),
      },
    },
  );

  if (!Array.isArray(data)) {
    throw new ApiError("历史消息响应不是数组。");
  }

  // 后端已经选取最近 50 条可见消息，
  // 并按消息 ID 升序返回，不在前端再次倒序。
  //
  // 不捕获并吞掉 401、404 等错误，
  // 留给组件决定清除登录状态还是显示错误。
  return data.map((item: unknown) => parseConversationMessage(item));
}
