from __future__ import annotations

import re

from app.models.evaluation import LLMEvaluationOutput

RULE_CAPS: dict[str, tuple[str, float]] = {
    "CLICHE_ANALYSIS": ("analysis_ability", 59.0),
    "NO_SAFETY_PLAN": ("organization_coordination", 65.0),
    "EMERGENCY_HARDLINE": ("emergency_response", 40.0),
    "INTERPERSONAL_CONFLICT": ("interpersonal_communication", 40.0),
}

_SAFETY_PLAN_PATTERN = re.compile(r"安全预案|应急预案|紧急预案|安全保障方案|经费预算|经费保障")


def _detect_violations_deterministically(transcript: str, question_type: str) -> set[str]:
    violations: set[str] = set()
    if question_type == "PLANNING_ORGANIZATION" and not _SAFETY_PLAN_PATTERN.search(transcript):
        violations.add("NO_SAFETY_PLAN")
    return violations


def apply_rule_caps(
    llm_output: LLMEvaluationOutput,
    transcript: str,
    question_type: str,
) -> LLMEvaluationOutput:
    output = llm_output.model_copy(deep=True)
    all_violations = set(output.rule_violations) | _detect_violations_deterministically(
        transcript=transcript,
        question_type=question_type,
    )

    for violation in all_violations:
        if violation not in RULE_CAPS:
            continue
        field_name, cap_value = RULE_CAPS[violation]
        dimension = getattr(output, field_name)
        if dimension.score > cap_value:
            dimension.score = cap_value

    return output

