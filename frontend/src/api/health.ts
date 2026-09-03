import { ApiError, apiRequest } from "./client";

export type ReadinessResponse = {
  status: "ready";
};

export async function getReadiness(): Promise<ReadinessResponse> {
  const data = await apiRequest<unknown>("/health/ready");

  if (
    typeof data !== "object" ||
    data === null ||
    !("status" in data) ||
    data.status !== "ready"
  ) {
    throw new ApiError("健康检查响应格式不符合预期。");
  }

  return {
    status: data.status,
  };
}
