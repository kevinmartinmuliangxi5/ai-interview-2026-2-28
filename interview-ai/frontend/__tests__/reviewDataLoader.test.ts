import { loadEvaluationById } from "@/lib/reviewDataLoader";
import type { EvaluationResult } from "@/types/evaluation";

const MOCK_EVALUATION: EvaluationResult = {
  id: "ev-1",
  user_id: "user-1",
  question_id: "q-1",
  transcript: "测试转写",
  transcript_segments: [{ text: "测试", start: 0, end: 1.2 }],
  audio_duration_seconds: 12.5,
  audio_storage_path: null,
  analysis_ability_score: 80,
  analysis_ability_reasoning: "分析较完整",
  organization_coordination_score: 82,
  organization_coordination_reasoning: "组织结构清晰",
  emergency_response_score: 79,
  emergency_response_reasoning: "应急流程完整",
  interpersonal_communication_score: 85,
  interpersonal_communication_reasoning: "沟通表达自然",
  language_expression_score: 81,
  language_expression_reasoning: "语言流畅",
  job_matching_score: 88,
  job_matching_reasoning: "岗位匹配度高",
  paralinguistic_fluency_score: 77,
  pause_count: null,
  speech_rate_cpm: null,
  filler_density_per_min: null,
  structural_framework_check: {
    is_complete: true,
    missing_elements: [],
    present_elements: ["表明态度", "分析原因", "提出对策"],
  },
  improvement_suggestions: ["补充复盘闭环"],
  model_ideal_answer: "示范答案",
  rule_violations: [],
  anti_template_warning: null,
  final_score: 82.7,
  created_at: "2026-03-03T08:00:00Z",
  client_request_id: null,
};

describe("loadEvaluationById", () => {
  it("returns evaluation payload for 200 response", async () => {
    const mockFetch = jest.fn().mockResolvedValue({
      status: 200,
      ok: true,
      json: async () => MOCK_EVALUATION,
    });

    const result = await loadEvaluationById({
      backendUrl: "http://localhost:8000",
      evaluationId: "ev-1",
      accessToken: "token",
      fetchImpl: mockFetch,
    });

    expect(result.state).toBe("success");
    if (result.state === "success") {
      expect(result.evaluation.id).toBe("ev-1");
    }
  });

  it("returns not_found for 404 response", async () => {
    const mockFetch = jest.fn().mockResolvedValue({
      status: 404,
      ok: false,
      json: async () => ({ detail: { error_code: "ERR_NOT_FOUND", message: "记录不存在" } }),
    });

    const result = await loadEvaluationById({
      backendUrl: "http://localhost:8000",
      evaluationId: "missing",
      accessToken: "token",
      fetchImpl: mockFetch,
    });

    expect(result).toEqual({ state: "not_found" });
  });

  it("returns unauthorized for 401 response", async () => {
    const mockFetch = jest.fn().mockResolvedValue({
      status: 401,
      ok: false,
      json: async () => ({ detail: { error_code: "ERR_UNAUTHORIZED" } }),
    });

    const result = await loadEvaluationById({
      backendUrl: "http://localhost:8000",
      evaluationId: "ev-1",
      accessToken: "expired",
      fetchImpl: mockFetch,
    });

    expect(result).toEqual({ state: "unauthorized" });
  });
});
