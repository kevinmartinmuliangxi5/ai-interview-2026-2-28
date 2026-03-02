from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from typing import Any


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def analyze_vocab(
    transcript: str,
    question_type: str,
    keyword_dict: dict[str, list[str]],
) -> dict[str, Any]:
    normalized = _normalize(transcript)
    required = list(dict.fromkeys(keyword_dict.get(question_type, [])))
    required_count = len(required)

    matched = [word for word in required if _normalize(word) in normalized]
    policy_coverage = (len(matched) / required_count) if required_count else None

    cliche_blacklist = keyword_dict.get("CLICHE_BLACKLIST", [])
    cliche_count = 0
    for phrase in cliche_blacklist:
        if _normalize(phrase) in normalized:
            cliche_count += 1

    return {
        "policy_coverage": policy_coverage,
        "matched_keywords": matched,
        "required_count": required_count,
        "matched_count": len(matched),
        "cliche_count": cliche_count,
    }


def check_anti_template(transcript: str, patterns: Iterable[str]) -> str | None:
    normalized = _normalize(transcript)
    hit_count = 0
    for pattern in patterns:
        if re.search(pattern, normalized):
            hit_count += 1

    if hit_count >= 3:
        return f"检测到高频套话模式，命中 {hit_count} 条黑名单词组，建议结合具体情境重组答案结构。"
    return None

