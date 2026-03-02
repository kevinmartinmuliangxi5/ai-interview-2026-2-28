from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

RuleViolation = Literal[
    "CLICHE_ANALYSIS",
    "NO_SAFETY_PLAN",
    "EMERGENCY_HARDLINE",
    "INTERPERSONAL_CONFLICT",
]

_VALID_VIOLATIONS: set[str] = {
    "CLICHE_ANALYSIS",
    "NO_SAFETY_PLAN",
    "EMERGENCY_HARDLINE",
    "INTERPERSONAL_CONFLICT",
}


class DimensionScore(BaseModel):
    score: float = Field(..., ge=0.0, le=100.0)
    reasoning: str


class StructuralCheck(BaseModel):
    is_complete: bool
    missing_elements: list[str]
    present_elements: list[str]


class LLMEvaluationOutput(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    analysis_ability: DimensionScore
    organization_coordination: DimensionScore
    emergency_response: DimensionScore
    interpersonal_communication: DimensionScore
    language_expression: DimensionScore
    job_matching: DimensionScore
    structural_framework_check: StructuralCheck
    improvement_suggestions: list[str]
    model_ideal_answer: str
    rule_violations: list[RuleViolation] = Field(default_factory=list)

    @field_validator("rule_violations", mode="before")
    @classmethod
    def filter_unknown_violations(cls, value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, str) and item in _VALID_VIOLATIONS]


class InterviewResult(BaseModel):
    llm_output: LLMEvaluationOutput
    paralinguistic_fluency_score: float = Field(..., ge=0.0, le=100.0)

    def final_score(self) -> float:
        d = self.llm_output
        return round(
            d.analysis_ability.score * 0.20
            + d.organization_coordination.score * 0.15
            + d.emergency_response.score * 0.15
            + d.interpersonal_communication.score * 0.15
            + d.language_expression.score * 0.15
            + d.job_matching.score * 0.10
            + self.paralinguistic_fluency_score * 0.10,
            2,
        )
