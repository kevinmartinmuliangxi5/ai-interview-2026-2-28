import json
import re
from pathlib import Path

QUESTION_TYPES = {
    'COMPREHENSIVE_ANALYSIS',
    'PLANNING_ORGANIZATION',
    'EMERGENCY_RESPONSE',
    'INTERPERSONAL_RELATIONSHIPS',
    'SELF_COGNITION',
    'SCENARIO_SIMULATION',
}


def test_data_files_contract() -> None:
    root = Path(__file__).resolve().parents[1]
    data_dir = root / 'app' / 'data'

    questions = json.loads((data_dir / 'questions.json').read_text(encoding='utf-8'))
    assert len(questions) == 18
    assert all(q['question_type'] in QUESTION_TYPES for q in questions)

    keyword_dict = json.loads((data_dir / 'keyword_dict.json').read_text(encoding='utf-8'))
    assert len(keyword_dict) == 6

    patterns = json.loads((data_dir / 'cliche_patterns.json').read_text(encoding='utf-8'))
    assert len(patterns) >= 15
    for pattern in patterns:
        re.compile(pattern)
