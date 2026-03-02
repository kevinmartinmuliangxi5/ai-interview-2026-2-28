from __future__ import annotations

import pytest

from app.services.prompt_factory import build_system_prompt


def test_planning_prompt_contains_five_steps() -> None:
    prompt = build_system_prompt('PLANNING_ORGANIZATION', policy_coverage=0.7, cliche_count=1)
    assert '定、摸、筹、控、结' in prompt


def test_emergency_prompt_contains_six_words() -> None:
    prompt = build_system_prompt('EMERGENCY_RESPONSE', policy_coverage=0.8, cliche_count=0)
    assert '稳、明、调、解、报、总' in prompt


def test_prompt_hides_policy_when_none() -> None:
    prompt = build_system_prompt('COMPREHENSIVE_ANALYSIS', policy_coverage=None, cliche_count=0)
    assert 'policy_coverage' not in prompt


def test_prompt_hides_cliche_hint_when_zero() -> None:
    prompt = build_system_prompt('COMPREHENSIVE_ANALYSIS', policy_coverage=0.8, cliche_count=0)
    assert '套话命中数' not in prompt


@pytest.mark.parametrize(
    'question_type',
    [
        'COMPREHENSIVE_ANALYSIS',
        'PLANNING_ORGANIZATION',
        'EMERGENCY_RESPONSE',
        'INTERPERSONAL_RELATIONSHIPS',
        'SELF_COGNITION',
        'SCENARIO_SIMULATION',
    ],
)
def test_all_question_types_supported(question_type: str) -> None:
    prompt = build_system_prompt(question_type, policy_coverage=0.5, cliche_count=1)
    assert isinstance(prompt, str)
    assert len(prompt) > 0
