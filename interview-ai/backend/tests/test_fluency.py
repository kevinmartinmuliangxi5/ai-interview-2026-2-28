from __future__ import annotations

from app.services.fluency import calculate_fluency_score


def test_empty_segments_returns_base_score() -> None:
    assert calculate_fluency_score([]) == 80.0


def test_normal_segments_keep_base_score() -> None:
    segments = [
        {'text': 'a' * 200, 'start': 0.0, 'end': 50.0},
        {'text': 'b' * 20, 'start': 50.5, 'end': 60.0},
    ]
    assert calculate_fluency_score(segments, transcript='') == 80.0


def test_five_pauses_deduct_to_70() -> None:
    segments = [
        {'text': 'a' * 50, 'start': 0.0, 'end': 10.0},
        {'text': 'a' * 50, 'start': 13.0, 'end': 23.0},
        {'text': 'a' * 50, 'start': 26.0, 'end': 36.0},
        {'text': 'a' * 50, 'start': 39.0, 'end': 49.0},
        {'text': 'a' * 50, 'start': 52.0, 'end': 62.0},
        {'text': 'a' * 50, 'start': 65.0, 'end': 75.0},
    ]
    assert calculate_fluency_score(segments, transcript='') == 70.0


def test_pause_deduction_has_upper_bound_10() -> None:
    segments = [
        {'text': 'a' * 35, 'start': 0.0, 'end': 5.0},
        {'text': 'a' * 35, 'start': 8.0, 'end': 13.0},
        {'text': 'a' * 35, 'start': 16.0, 'end': 21.0},
        {'text': 'a' * 35, 'start': 24.0, 'end': 29.0},
        {'text': 'a' * 35, 'start': 32.0, 'end': 37.0},
        {'text': 'a' * 35, 'start': 40.0, 'end': 45.0},
        {'text': 'a' * 35, 'start': 48.0, 'end': 53.0},
        {'text': 'a' * 35, 'start': 56.0, 'end': 61.0},
        {'text': 'a' * 35, 'start': 64.0, 'end': 69.0},
    ]
    assert calculate_fluency_score(segments, transcript='') == 70.0


def test_low_speech_rate_deducts_5() -> None:
    segments = [{'text': 'a' * 140, 'start': 0.0, 'end': 60.0}]
    assert calculate_fluency_score(segments, transcript='') == 75.0


def test_filler_density_over_5_per_minute_deducts_3() -> None:
    segments = [{'text': 'a' * 200, 'start': 0.0, 'end': 60.0}]
    transcript = '那个那个那个那个那个那个'
    assert calculate_fluency_score(segments, transcript=transcript) == 77.0


def test_floor_score_is_50() -> None:
    segments = [
        {'text': 'a' * 20, 'start': 0.0, 'end': 10.0},
        {'text': 'a' * 20, 'start': 14.0, 'end': 24.0},
        {'text': 'a' * 20, 'start': 28.0, 'end': 38.0},
        {'text': 'a' * 20, 'start': 42.0, 'end': 52.0},
        {'text': 'a' * 20, 'start': 56.0, 'end': 66.0},
        {'text': 'a' * 20, 'start': 70.0, 'end': 80.0},
        {'text': 'a' * 20, 'start': 84.0, 'end': 94.0},
        {'text': 'a' * 20, 'start': 98.0, 'end': 108.0},
        {'text': 'a' * 20, 'start': 112.0, 'end': 122.0},
    ]
    transcript = '那个那个那个那个那个那个然后然后然后然后然后然后'
    assert calculate_fluency_score(segments, transcript=transcript) == 50.0
