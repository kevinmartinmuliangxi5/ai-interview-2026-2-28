from __future__ import annotations

import pytest
from pydantic import ValidationError



def test_score_over_100_raises_validation_error() -> None:
    from app.models.evaluation import DimensionScore

    with pytest.raises(ValidationError):
        DimensionScore(score=101, reasoning='bad')



def test_filter_unknown_rule_violations() -> None:
    from app.models.evaluation import DimensionScore, LLMEvaluationOutput, StructuralCheck

    payload = LLMEvaluationOutput(
        analysis_ability=DimensionScore(score=80, reasoning='ok'),
        organization_coordination=DimensionScore(score=80, reasoning='ok'),
        emergency_response=DimensionScore(score=80, reasoning='ok'),
        interpersonal_communication=DimensionScore(score=80, reasoning='ok'),
        language_expression=DimensionScore(score=80, reasoning='ok'),
        job_matching=DimensionScore(score=80, reasoning='ok'),
        structural_framework_check=StructuralCheck(
            is_complete=False,
            missing_elements=['长效机制'],
            present_elements=['情绪安抚']
        ),
        improvement_suggestions=['补充长效机制'],
        model_ideal_answer='示例答案',
        rule_violations=['EMERGENCY-HARDLINE', 'NO_SAFETY_PLAN'],
    )

    assert payload.rule_violations == ['NO_SAFETY_PLAN']



def test_final_score_weight_formula() -> None:
    from app.models.evaluation import DimensionScore, InterviewResult, LLMEvaluationOutput, StructuralCheck

    llm_output = LLMEvaluationOutput(
        analysis_ability=DimensionScore(score=80, reasoning='a'),
        organization_coordination=DimensionScore(score=70, reasoning='b'),
        emergency_response=DimensionScore(score=90, reasoning='c'),
        interpersonal_communication=DimensionScore(score=60, reasoning='d'),
        language_expression=DimensionScore(score=85, reasoning='e'),
        job_matching=DimensionScore(score=75, reasoning='f'),
        structural_framework_check=StructuralCheck(
            is_complete=True,
            missing_elements=[],
            present_elements=['完整']
        ),
        improvement_suggestions=['ok'],
        model_ideal_answer='ok',
        rule_violations=[],
    )
    result = InterviewResult(llm_output=llm_output, paralinguistic_fluency_score=88)

    expected = round(80*0.20 + 70*0.15 + 90*0.15 + 60*0.15 + 85*0.15 + 75*0.10 + 88*0.10, 2)
    assert result.final_score() == expected
