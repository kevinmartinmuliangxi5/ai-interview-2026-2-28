from __future__ import annotations

from app.services.vocab_analyzer import analyze_vocab, check_anti_template



def test_policy_coverage_is_none_when_required_count_zero() -> None:
    result = analyze_vocab(
        transcript='任意文本',
        question_type='SELF_COGNITION',
        keyword_dict={'SELF_COGNITION': []},
    )
    assert result['policy_coverage'] is None



def test_policy_coverage_calculation_two_of_four() -> None:
    result = analyze_vocab(
        transcript='法治中国建设与接诉即办都很重要。',
        question_type='COMPREHENSIVE_ANALYSIS',
        keyword_dict={'COMPREHENSIVE_ANALYSIS': ['法治中国建设', '接诉即办', '共同富裕', '乡村振兴']},
    )
    assert result['policy_coverage'] == 0.5



def test_anti_template_warning_not_triggered_with_two_hits() -> None:
    warning = check_anti_template(
        transcript='随着时代的发展，我们要坚持以人为本。',
        patterns=['随着.{0,10}的发展', '坚持以人为本', '不断创新.{0,8}方式'],
    )
    assert warning is None



def test_anti_template_warning_triggered_with_three_hits() -> None:
    warning = check_anti_template(
        transcript='随着时代的发展，我们要坚持以人为本，并不断创新工作方式。',
        patterns=['随着.{0,10}的发展', '坚持以人为本', '不断创新.{0,8}方式'],
    )
    assert isinstance(warning, str)
    assert warning
