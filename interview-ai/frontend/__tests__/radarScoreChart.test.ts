import { buildRadarScoreData } from "@/components/review/RadarScoreChart";
import type { EvaluationResult } from "@/types/evaluation";

const SAMPLE_EVALUATION: EvaluationResult = {
  id: "ev-2",
  user_id: "user-1",
  question_id: "q-1",
  transcript: "测试",
  transcript_segments: [],
  audio_duration_seconds: 1,
  audio_storage_path: null,
  analysis_ability_score: 71,
  analysis_ability_reasoning: "",
  organization_coordination_score: 72,
  organization_coordination_reasoning: "",
  emergency_response_score: 73,
  emergency_response_reasoning: "",
  interpersonal_communication_score: 74,
  interpersonal_communication_reasoning: "",
  language_expression_score: 75,
  language_expression_reasoning: "",
  job_matching_score: 76,
  job_matching_reasoning: "",
  paralinguistic_fluency_score: 77,
  pause_count: null,
  speech_rate_cpm: null,
  filler_density_per_min: null,
  structural_framework_check: { is_complete: true, missing_elements: [], present_elements: [] },
  improvement_suggestions: [],
  model_ideal_answer: "",
  rule_violations: [],
  anti_template_warning: null,
  final_score: 74,
  created_at: "2026-03-03T08:00:00Z",
  client_request_id: null,
};

describe("buildRadarScoreData", () => {
  it("maps evaluation to seven dimensions", () => {
    const data = buildRadarScoreData(SAMPLE_EVALUATION);

    expect(data).toHaveLength(7);
    expect(data.map((item) => item.label)).toEqual([
      "综合分析",
      "计划组织协调",
      "应急应变",
      "人际沟通",
      "语言表达",
      "岗位匹配",
      "副语言流畅度",
    ]);
  });

  it("keeps score and weight aligned with PRD formula", () => {
    const data = buildRadarScoreData(SAMPLE_EVALUATION);

    expect(data[0].score).toBe(71);
    expect(data[0].weight).toBe("20%");
    expect(data[5].score).toBe(76);
    expect(data[5].weight).toBe("10%");
    expect(data[6].score).toBe(77);
    expect(data[6].weight).toBe("10%");
  });
});
