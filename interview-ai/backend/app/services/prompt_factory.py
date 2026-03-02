from __future__ import annotations


def _prompt_by_type(question_type: str) -> str:
    if question_type == "COMPREHENSIVE_ANALYSIS":
        return "请按“点、析、对、升”四段论评估回答质量，强调问题本质与治理路径。"
    if question_type == "PLANNING_ORGANIZATION":
        return (
            "请按“定、摸、筹、控、结”五步评估组织类回答。"
            "若缺失安全预案或经费安排，必须在 rule_violations 中标记 NO_SAFETY_PLAN。"
        )
    if question_type == "EMERGENCY_RESPONSE":
        return (
            "请按“稳、明、调、解、报、总”六字诀评估应急处置。"
            "若出现暴力驱离、推诿责任等表述，必须标记 EMERGENCY_HARDLINE。"
        )
    if question_type == "INTERPERSONAL_RELATIONSHIPS":
        return "重点评估尊重服从、委婉沟通、协同推进，不鼓励对抗叙事。"
    if question_type == "SELF_COGNITION":
        return "重点评估岗位匹配、价值认同、成长规划与责任意识。"
    if question_type == "SCENARIO_SIMULATION":
        return "重点评估场景还原、表达结构、可执行步骤与结果闭环。"
    raise ValueError(f"Unsupported question_type: {question_type}")


def build_system_prompt(
    question_type: str,
    policy_coverage: float | None,
    cliche_count: int,
) -> str:
    base = [
        "你是公务员结构化面试评估官。输出必须符合 Pydantic 结构。",
        _prompt_by_type(question_type),
        (
            "rule_violations 仅允许以下枚举："
            "CLICHE_ANALYSIS, NO_SAFETY_PLAN, EMERGENCY_HARDLINE, INTERPERSONAL_CONFLICT。"
        ),
    ]

    if policy_coverage is not None:
        base.append(f"policy_coverage={policy_coverage:.2f}")
    if cliche_count > 0:
        base.append(f"套话命中数={cliche_count}")

    return "\n".join(base)

