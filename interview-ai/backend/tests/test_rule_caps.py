from __future__ import annotations

from app.models.evaluation import DimensionScore, LLMEvaluationOutput, StructuralCheck
from app.services.rule_caps import apply_rule_caps


def _make_output(score: float = 90.0, rule_violations: list[str] | None = None) -> LLMEvaluationOutput:
    return LLMEvaluationOutput(
        analysis_ability=DimensionScore(score=score, reasoning='a'),
        organization_coordination=DimensionScore(score=score, reasoning='b'),
        emergency_response=DimensionScore(score=score, reasoning='c'),
        interpersonal_communication=DimensionScore(score=score, reasoning='d'),
        language_expression=DimensionScore(score=score, reasoning='e'),
        job_matching=DimensionScore(score=score, reasoning='f'),
        structural_framework_check=StructuralCheck(
            is_complete=False,
            missing_elements=['长效机制'],
            present_elements=['情绪安抚'],
        ),
        improvement_suggestions=['x'],
        model_ideal_answer='y',
        rule_violations=rule_violations or [],
    )


def test_llm_emergency_hardline_caps_emergency_score() -> None:
    output = _make_output(rule_violations=['EMERGENCY_HARDLINE'])
    capped = apply_rule_caps(output, transcript='无关文本', question_type='EMERGENCY_RESPONSE')
    assert capped.emergency_response.score == 40.0


def test_cap_does_not_increase_when_already_lower() -> None:
    output = _make_output(score=38.0, rule_violations=['EMERGENCY_HARDLINE'])
    capped = apply_rule_caps(output, transcript='无关文本', question_type='EMERGENCY_RESPONSE')
    assert capped.emergency_response.score == 38.0


def test_planning_without_safety_terms_triggers_no_safety_plan() -> None:
    output = _make_output(rule_violations=[])
    capped = apply_rule_caps(
        output,
        transcript='我会先调研再组织活动并做好复盘。',
        question_type='PLANNING_ORGANIZATION',
    )
    assert capped.organization_coordination.score == 65.0


def test_planning_with_safety_terms_not_triggered() -> None:
    output = _make_output(rule_violations=[])
    capped = apply_rule_caps(
        output,
        transcript='方案中包含安全预案和经费预算，并明确应急保障。',
        question_type='PLANNING_ORGANIZATION',
    )
    assert capped.organization_coordination.score == 90.0


def test_unknown_violation_variant_has_no_effect() -> None:
    output = _make_output(rule_violations=['EMERGENCY-HARDLINE'])
    capped = apply_rule_caps(output, transcript='无关文本', question_type='EMERGENCY_RESPONSE')
    assert capped.emergency_response.score == 90.0


def test_multiple_violations_cap_multiple_dimensions() -> None:
    output = _make_output(rule_violations=['EMERGENCY_HARDLINE', 'INTERPERSONAL_CONFLICT'])
    capped = apply_rule_caps(output, transcript='无关文本', question_type='EMERGENCY_RESPONSE')
    assert capped.emergency_response.score == 40.0
    assert capped.interpersonal_communication.score == 40.0
