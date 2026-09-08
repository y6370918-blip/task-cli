import { beforeEach, describe, expect, test, vi } from "vitest";

import { ApiError, apiRequest } from "./client";

// 为模拟函数保留 fetch 的参数和返回值类型。
// 每个测试开始时重新创建，避免调用记录和返回值互相影响。
let fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  fetchMock = vi.fn<typeof fetch>();

  // 替换全局 fetch，apiRequest 仍执行真实代码，
  // 但请求不会真正发送到网络。
  vi.stubGlobal("fetch", fetchMock);

  // 使用测试专用地址，不依赖本地 .env。
  // 故意添加末尾斜杠，验证 Client 会去掉多余斜杠。
  vi.stubEnv("VITE_API_BASE_URL", "http://api.test/");
});

// 公共 setup.ts 会在每个测试结束后恢复 fetch 和环境变量。
describe("apiRequest", () => {
  test("解析成功响应，并保留请求中的认证头", async () => {
    const payload = { status: "ready" };

    // 模拟 fetch 成功，返回真实 Response 对象。
    // 因此 response.json() 仍会执行真实 JSON 解析。
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const result = await apiRequest<{ status: string }>("/health/ready", {
      headers: {
        // 只是测试字符串，不是真实 JWT。
        Authorization: "Bearer test-token",
      },
    });

    // toEqual 比较对象内容，不要求是同一个对象引用。
    expect(result).toEqual(payload);
    expect(fetchMock).toHaveBeenCalledTimes(1);

    // objectContaining：只检查关心的属性，
    // 不要求 options 必须只有这些属性。
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/health/ready",
      expect.objectContaining({
        headers: expect.any(Headers),
      }),
    );

    // mock.calls 保存模拟函数每次收到的参数。
    // ?. 是可选链：不存在这一项时返回 undefined。
    const options = fetchMock.mock.calls[0]?.[1];
    const headers = new Headers(options?.headers);

    expect(headers.get("Accept")).toBe("application/json");
    expect(headers.get("Authorization")).toBe("Bearer test-token");
  });

  test("401 响应保留状态码与后端错误提示", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: "登录凭证无效" }), { status: 401 }),
    );

    // 保存同一次调用产生的 Promise，
    // 避免两条断言变成两次请求。
    const request = apiRequest("/auth/me");

    // rejects：检查 Promise 拒绝时的错误。
    // 必须 await，让测试等待异步断言完成。
    await expect(request).rejects.toBeInstanceOf(ApiError);
    await expect(request).rejects.toMatchObject({
      status: 401,
      message: "登录凭证无效",
    });
  });

  test("422 验证错误转换为统一提示", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: [
            {
              loc: ["body", "title"],
              msg: "Field required",
              type: "missing",
            },
          ],
        }),
        { status: 422 },
      ),
    );

    await expect(apiRequest("/tasks/")).rejects.toMatchObject({
      status: 422,
      message: "请求参数不符合要求，请检查输入。",
    });
  });

  test("网络失败没有 HTTP 状态码，不伪装成 401", async () => {
    // mockRejectedValue 模拟 fetch 自身失败。
    // 与服务器返回 401、503 不同，这里没有收到 HTTP 响应。
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));

    const request = apiRequest("/tasks/");

    await expect(request).rejects.toBeInstanceOf(ApiError);
    await expect(request).rejects.toMatchObject({
      status: null,
      message: "无法连接后端，请检查服务、网络或跨域配置。",
    });
  });

  test("200 响应不是有效 JSON 时给出明确错误", async () => {
    fetchMock.mockResolvedValue(
      new Response("<html>不是 JSON</html>", {
        status: 200,
        headers: { "Content-Type": "text/html" },
      }),
    );

    // HTTP 成功不代表响应内容符合 API 协议。
    await expect(apiRequest("/tasks/")).rejects.toMatchObject({
      status: 200,
      message: "后端返回的内容不是有效 JSON。",
    });
  });
});
