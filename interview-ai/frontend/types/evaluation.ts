export interface TranscriptSegment {
  text: string;
  start: number;
  end: number;
}

export interface StructuralFrameworkCheck {
  is_complete: boolean;
  missing_elements: string[];
  present_elements: string[];
}

export interface EvaluationResult {
  id: string;
  user_id: string;
  question_id: string | null;
  transcript: string;
  transcript_segments: TranscriptSegment[];
  audio_duration_seconds: number;
  audio_storage_path: string | null;
  analysis_ability_score: number;
  analysis_ability_reasoning: string;
  organization_coordination_score: number;
  organization_coordination_reasoning: string;
  emergency_response_score: number;
  emergency_response_reasoning: string;
  interpersonal_communication_score: number;
  interpersonal_communication_reasoning: string;
  language_expression_score: number;
  language_expression_reasoning: string;
  job_matching_score: number;
  job_matching_reasoning: string;
  paralinguistic_fluency_score: number;
  pause_count: number | null;
  speech_rate_cpm: number | null;
  filler_density_per_min: number | null;
  structural_framework_check: StructuralFrameworkCheck;
  improvement_suggestions: string[];
  model_ideal_answer: string;
  rule_violations: string[];
  anti_template_warning: string | null;
  final_score: number;
  created_at: string;
  client_request_id: string | null;
}
