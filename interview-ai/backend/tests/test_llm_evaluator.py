from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.evaluation import DimensionScore, LLMEvaluationOutput, StructuralCheck
from app.services.llm_evaluator import DEFAULT_LLM_MODEL, LLMParseError, run_llm_evaluation


def _valid_parsed_output() -> LLMEvaluationOutput:
    return LLMEvaluationOutput(
        analysis_ability=DimensionScore(score=80, reasoning='a'),
        organization_coordination=DimensionScore(score=80, reasoning='b'),
        emergency_response=DimensionScore(score=80, reasoning='c'),
        interpersonal_communication=DimensionScore(score=80, reasoning='d'),
        language_expression=DimensionScore(score=80, reasoning='e'),
        job_matching=DimensionScore(score=80, reasoning='f'),
        structural_framework_check=StructuralCheck(
            is_complete=True,
            missing_elements=[],
            present_elements=['完整'],
        ),
        improvement_suggestions=['ok'],
        model_ideal_answer='ok',
        rule_violations=[],
    )


def _mock_completion(content: str, refusal: str | None = None) -> SimpleNamespace:
    message = SimpleNamespace(content=content, refusal=refusal)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice])


@pytest.mark.asyncio
async def test_llm_evaluation_success() -> None:
    openai_client = MagicMock()
    openai_client.chat.completions.create = AsyncMock(
        return_value=_mock_completion(_valid_parsed_output().model_dump_json())
    )

    result = await run_llm_evaluation(
        transcript='回答内容',
        question={'content': '题目', 'question_type': 'COMPREHENSIVE_ANALYSIS'},
        policy_coverage=0.8,
        cliche_count=1,
        openai_client=openai_client,
    )

    assert isinstance(result, LLMEvaluationOutput)


@pytest.mark.asyncio
async def test_llm_model_fallback_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv('OPENAI_MODEL', raising=False)

    openai_client = MagicMock()
    openai_client.chat.completions.create = AsyncMock(
        return_value=_mock_completion(_valid_parsed_output().model_dump_json())
    )

    await run_llm_evaluation(
        transcript='回答内容',
        question={'content': '题目', 'question_type': 'COMPREHENSIVE_ANALYSIS'},
        policy_coverage=0.8,
        cliche_count=0,
        openai_client=openai_client,
    )

    kwargs = openai_client.chat.completions.create.await_args.kwargs
    assert kwargs['model'] == DEFAULT_LLM_MODEL
    assert kwargs['response_format'] == {'type': 'json_object'}


@pytest.mark.asyncio
async def test_llm_parse_failure_after_retries() -> None:
    openai_client = MagicMock()
    openai_client.chat.completions.create = AsyncMock(
        side_effect=[ValueError('invalid'), ValueError('invalid'), ValueError('invalid')]
    )

    with pytest.raises(LLMParseError):
        await run_llm_evaluation(
            transcript='回答内容',
            question={'content': '题目', 'question_type': 'COMPREHENSIVE_ANALYSIS'},
            policy_coverage=None,
            cliche_count=0,
            openai_client=openai_client,
        )
