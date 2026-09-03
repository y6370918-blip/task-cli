export class ApiError extends Error {
  readonly status: number | null;

  constructor(message: string, status: number | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function getApiBaseUrl(): string {
  const value = import.meta.env.VITE_API_BASE_URL?.trim();

  if (!value) {
    throw new ApiError("未配置 VITE_API_BASE_URL。");
  }

  return value.replace(/\/+$/, "");
}

function getErrorMessage(data: unknown, status: number): string {
  if (typeof data === "object" && data !== null) {
    if ("detail" in data && typeof data.detail === "string") {
      return data.detail;
    }

    if ("detail" in data && Array.isArray(data.detail)) {
      return "请求参数不符合要求，请检查输入。";
    }

    if ("message" in data && typeof data.message === "string") {
      return data.message;
    }
  }

  return `请求失败（HTTP ${status}）。`;
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");

  let response: Response;

  try {
    response = await fetch(`${baseUrl}${path}`, {
      ...options,
      headers,
    });
  } catch (error: unknown) {
    if (error instanceof Error && error.name === "AbortError") {
      throw error;
    }

    throw new ApiError("无法连接后端，请检查服务、网络或跨域配置。");
  }

  let data: unknown;

  try {
    data = await response.json();
  } catch (error: unknown) {
    if (error instanceof Error && error.name === "AbortError") {
      throw error;
    }

    const message = response.ok
      ? "后端返回的内容不是有效 JSON。"
      : `请求失败（HTTP ${response.status}）。`;

    throw new ApiError(message, response.status);
  }

  if (!response.ok) {
    throw new ApiError(getErrorMessage(data, response.status), response.status);
  }

  return data as T;
}
