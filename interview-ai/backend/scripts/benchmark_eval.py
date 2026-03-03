from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.models.evaluation import InterviewResult
from app.services.llm_evaluator import run_llm_evaluation


@dataclass(frozen=True)
class BenchmarkQuestion:
    question_id: str
    question_type: str
    content: str
    transcript: str


BENCHMARK_QUESTIONS: list[BenchmarkQuestion] = [
    BenchmarkQuestion(
        question_id="bench-qa-01",
        question_type="COMPREHENSIVE_ANALYSIS",
        content="请分析基层单位在接诉即办中的常见堵点，并给出改进路径。",
        transcript="我会先明确问题本质，再按制度、流程、协同、监督四个层面逐项解决。",
    ),
    BenchmarkQuestion(
        question_id="bench-qa-02",
        question_type="PLANNING_ORGANIZATION",
        content="请你组织一次社区防汛演练，说明计划与分工。",
        transcript="我将制定时间表、职责表、物资清单和应急预案，按节点推进演练。",
    ),
    BenchmarkQuestion(
        question_id="bench-qa-03",
        question_type="EMERGENCY_RESPONSE",
        content="社区突发停水并出现抢水秩序混乱，你如何处置？",
        transcript="先稳秩序、再保底线、后查原因、再复盘，确保信息公开和部门联动。",
    ),
    BenchmarkQuestion(
        question_id="bench-qa-04",
        question_type="INTERPERSONAL_RELATIONSHIPS",
        content="同事对你工作方式有意见并公开质疑，你如何处理？",
        transcript="我会先沟通事实和目标，分歧聚焦在问题本身，形成共识后再落地改进。",
    ),
    BenchmarkQuestion(
        question_id="bench-qa-05",
        question_type="SELF_COGNITION",
        content="请谈谈你的岗位匹配度与改进方向。",
        transcript="我匹配岗位要求的执行力和沟通力，同时持续补齐政策研究与复盘能力。",
    ),
]

RESULT_HEADER = """# Benchmark Results (PRD §5.2)
目标：20 道题各 5 次，total_score 极差 ≤ 3 分。

| Date | Question ID | Type | Min | Max | Range | Status |
|------|-------------|------|-----|-----|-------|--------|
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark LLM scoring consistency.")
    parser.add_argument("--dry-run", action="store_true", help="Skip real LLM calls and write mock records.")
    parser.add_argument("--runs", type=int, default=5, help="How many times each question is evaluated.")
    return parser.parse_args()


def ensure_results_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(RESULT_HEADER, encoding="utf-8")
        return

    content = path.read_text(encoding="utf-8")
    if "| Date | Question ID | Type | Min | Max | Range | Status |" not in content:
        path.write_text(RESULT_HEADER, encoding="utf-8")


def append_rows(path: Path, rows: list[str]) -> None:
    with path.open("a", encoding="utf-8") as file:
        for row in rows:
            file.write(f"{row}\n")


def summarize_rows(rows: list[tuple[str, str, float, float, float, str]]) -> str:
    lines = ["Benchmark summary:"]
    for question_id, question_type, min_score, max_score, score_range, status in rows:
        lines.append(
            f"- {question_id} ({question_type}): min={min_score:.2f}, max={max_score:.2f}, "
            f"range={score_range:.2f}, status={status}"
        )
    return "\n".join(lines)


async def evaluate_scores(
    question: BenchmarkQuestion,
    runs: int,
    dry_run: bool,
    semaphore: asyncio.Semaphore,
) -> list[float]:
    if dry_run:
        return [82.0] * runs

    async def _run_once() -> float:
        async with semaphore:
            llm_output = await run_llm_evaluation(
                transcript=question.transcript,
                question={
                    "id": question.question_id,
                    "question_type": question.question_type,
                    "content": question.content,
                },
                policy_coverage=None,
                cliche_count=0,
            )
            interview_result = InterviewResult(
                llm_output=llm_output,
                paralinguistic_fluency_score=80.0,
            )
            return float(interview_result.final_score())

    return await asyncio.gather(*[_run_once() for _ in range(runs)])


async def main() -> int:
    args = parse_args()
    runs = max(1, args.runs)
    root = Path(__file__).resolve().parents[1]
    results_path = root / "docs" / "benchmark_results.md"
    ensure_results_file(results_path)

    semaphore = asyncio.Semaphore(5)
    row_values: list[tuple[str, str, float, float, float, str]] = []
    markdown_rows: list[str] = []
    today = date.today().isoformat()

    for question in BENCHMARK_QUESTIONS:
        scores = await evaluate_scores(question, runs, args.dry_run, semaphore)
        min_score = min(scores)
        max_score = max(scores)
        score_range = max_score - min_score
        if args.dry_run:
            status = "PASS (dry-run)"
        else:
            status = "PASS" if score_range <= 3 else "WARN"

        row_values.append((question.question_id, question.question_type, min_score, max_score, score_range, status))
        markdown_rows.append(
            f"| {today} | {question.question_id} | {question.question_type} | "
            f"{min_score:.2f} | {max_score:.2f} | {score_range:.2f} | {status} |"
        )

    append_rows(results_path, markdown_rows)
    print(summarize_rows(row_values))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
