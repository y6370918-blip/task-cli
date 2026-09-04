import { ApiError, apiRequest } from "./client";

export type AuthenticatedUser = {
  id: number;
  username: string;
  email: string;
};

export type RegisterInput = {
  username: string;
  email: string;
  password: string;
};

export type LoginInput = {
  username: string;
  password: string;
};

export type AccessToken = {
  accessToken: string;
  tokenType: "bearer";
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function parseUser(data: unknown): AuthenticatedUser {
  if (
    !isRecord(data) ||
    typeof data.id !== "number" ||
    !Number.isInteger(data.id) ||
    data.id <= 0 ||
    typeof data.username !== "string" ||
    data.username.trim() === "" ||
    typeof data.email !== "string" ||
    data.email.trim() === ""
  ) {
    throw new ApiError("用户响应格式不符合预期。");
  }

  return {
    id: data.id,
    username: data.username,
    email: data.email,
  };
}

function parseAccessToken(data: unknown): AccessToken {
  if (
    !isRecord(data) ||
    typeof data.access_token !== "string" ||
    data.access_token.trim() === "" ||
    data.token_type !== "bearer"
  ) {
    throw new ApiError("登录响应格式不符合预期。");
  }

  return {
    accessToken: data.access_token,
    tokenType: data.token_type,
  };
}

export async function registerUser(
  input: RegisterInput,
): Promise<AuthenticatedUser> {
  const data = await apiRequest<unknown>("/auth/register", {
    method: "POST",
    headers: {
      // 注册接口由 Pydantic UserCreate 接收 JSON。
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });

  return parseUser(data);
}

export async function loginUser(input: LoginInput): Promise<AccessToken> {
  const body = new URLSearchParams();

  // 登录接口使用 OAuth2PasswordRequestForm，
  // 所以不能像注册接口一样发送 JSON。
  //
  // URLSearchParams 会正确编码用户名或密码中的特殊字符，
  // 不应该手工拼接 `username=...&password=...`。
  body.set("username", input.username);
  body.set("password", input.password);

  const data = await apiRequest<unknown>("/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body,
  });

  return parseAccessToken(data);
}

export async function getCurrentUser(
  accessToken: string,
): Promise<AuthenticatedUser> {
  const data = await apiRequest<unknown>("/auth/me", {
    method: "GET",
    headers: {
      // `Bearer` 是认证方案，后面的字符串才是 JWT。
      // 后端 OAuth2PasswordBearer 会从这个请求头中提取 Token。
      Authorization: `Bearer ${accessToken}`,
    },
  });

  return parseUser(data);
}
