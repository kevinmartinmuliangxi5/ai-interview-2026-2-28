from __future__ import annotations

import asyncio
import os
from typing import Any

from app.models.evaluation import LLMEvaluationOutput
from app.services.prompt_factory import build_system_prompt


class LLMParseError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


async def run_llm_evaluation(
    transcript: str,
    question: dict[str, Any],
    policy_coverage: float | None,
    cliche_count: int,
    openai_client: Any | None = None,
    model: str | None = None,
) -> LLMEvaluationOutput:
    selected_model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    system_prompt = build_system_prompt(
        question_type=str(question["question_type"]),
        policy_coverage=policy_coverage,
        cliche_count=cliche_count,
    )

    if openai_client is None:
        from openai import AsyncOpenAI

        openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    last_error: Exception | None = None
    for attempt in range(3):  # initial + 2 retries
        try:
            completion = await openai_client.beta.chat.completions.parse(
                model=selected_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"题目：{question['content']}\n\n回答：{transcript}",
                    },
                ],
                response_format=LLMEvaluationOutput,
                temperature=0.2,
            )
            message = completion.choices[0].message
            if getattr(message, "refusal", None):
                raise LLMParseError(f"LLM refusal: {message.refusal}")
            parsed = getattr(message, "parsed", None)
            if parsed is None:
                raise LLMParseError("LLM parsed payload is empty.")
            return parsed
        except Exception as exc:
            last_error = exc
            if attempt == 2:
                break
            await asyncio.sleep(2**attempt)

    raise LLMParseError(str(last_error) if last_error else "Unknown LLM parse failure.")

