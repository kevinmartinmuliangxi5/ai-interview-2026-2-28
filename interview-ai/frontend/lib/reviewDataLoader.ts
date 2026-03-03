import type { EvaluationResult } from "@/types/evaluation";

interface LoaderParams {
  backendUrl: string;
  evaluationId: string;
  accessToken: string;
  fetchImpl?: typeof fetch;
}

type LoaderResult =
  | { state: "success"; evaluation: EvaluationResult }
  | { state: "not_found" }
  | { state: "unauthorized" }
  | { state: "error"; message: string };

function readErrorMessage(payload: unknown): string {
  if (typeof payload === "object" && payload !== null) {
    const data = payload as { message?: string; detail?: { message?: string } | string };
    if (typeof data.detail === "string") {
      return data.detail;
    }
    if (typeof data.detail?.message === "string") {
      return data.detail.message;
    }
    if (typeof data.message === "string") {
      return data.message;
    }
  }
  return "评估结果加载失败，请稍后重试。";
}

export async function loadEvaluationById({
  backendUrl,
  evaluationId,
  accessToken,
  fetchImpl = fetch,
}: LoaderParams): Promise<LoaderResult> {
  if (!backendUrl) {
    return { state: "error", message: "缺少 API_BASE_URL 配置。" };
  }

  const response = await fetchImpl(`${backendUrl}/api/v1/evaluations/${evaluationId}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    cache: "no-store",
  });

  if (response.status === 404) {
    return { state: "not_found" };
  }

  if (response.status === 401) {
    return { state: "unauthorized" };
  }

  const payload = await response.json();
  if (!response.ok) {
    return { state: "error", message: readErrorMessage(payload) };
  }

  return { state: "success", evaluation: payload as EvaluationResult };
}
