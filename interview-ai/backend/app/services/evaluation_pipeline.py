from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, Request, UploadFile

from app.models.evaluation import (
    DimensionScore,
    InterviewResult,
    LLMEvaluationOutput,
    StructuralCheck,
)
from app.services.asr import ASRTimeoutError, run_asr
from app.services.audio_processor import AudioValidationError, transcode_to_wav, validate_audio
from app.services.fluency import calculate_fluency_score
from app.services.llm_evaluator import LLMParseError, run_llm_evaluation
from app.services.rule_caps import apply_rule_caps
from app.services.vocab_analyzer import analyze_vocab, check_anti_template


def _find_question(request: Request, question_id: str) -> dict[str, Any] | None:
    cache = getattr(request.app.state, "question_cache", None)
    if cache is None:
        cache = {}
        request.app.state.question_cache = cache
    if question_id in cache:
        return cache[question_id]

    questions = getattr(request.app.state, "questions", [])
    for question in questions:
        if question.get("id") == question_id:
            cache[question_id] = question
            return question
    return None


async def _upload_to_storage(request: Request, user_id: str, audio_bytes: bytes) -> str:
    path = f"interview-audio/{user_id}/{datetime.now(UTC).date()}/{uuid4()}.wav"
    supabase = getattr(request.app.state, "supabase", None)
    if supabase is None:
        return path
    try:
        await supabase.storage.from_("interview-audio").upload(path, audio_bytes)  # type: ignore[attr-defined]
    except Exception:
        return path
    return path


def _default_llm_output() -> LLMEvaluationOutput:
    score = DimensionScore(score=80.0, reasoning="本地降级输出：未接入远程 LLM。")
    return LLMEvaluationOutput(
        analysis_ability=score,
        organization_coordination=score,
        emergency_response=score,
        interpersonal_communication=score,
        language_expression=score,
        job_matching=score,
        structural_framework_check=StructuralCheck(
            is_complete=False,
            missing_elements=["长效机制"],
            present_elements=["情绪安抚", "信息澄清"],
        ),
        improvement_suggestions=["补充长效机制与跨部门闭环。"],
        model_ideal_answer="请结合真实场景给出结构化答题示例。",
        rule_violations=[],
    )


async def _run_llm_or_fallback(
    request: Request,
    transcript: str,
    question: dict[str, Any],
    policy_coverage: float | None,
    cliche_count: int,
) -> LLMEvaluationOutput:
    openai_client = getattr(request.app.state, "openai", None)
    if openai_client is None:
        return _default_llm_output()
    return await run_llm_evaluation(
        transcript=transcript,
        question=question,
        policy_coverage=policy_coverage,
        cliche_count=cliche_count,
        openai_client=openai_client,
    )


def _build_response_payload(
    *,
    record_id: str,
    user_id: str,
    question: dict[str, Any],
    transcript: str,
    transcript_segments: list[dict[str, Any]],
    audio_duration_seconds: float,
    audio_storage_path: str,
    llm_output: LLMEvaluationOutput,
    anti_template_warning: str | None,
    paralinguistic_fluency_score: float,
    final_score: float,
) -> dict[str, Any]:
    return {
        "id": record_id,
        "user_id": user_id,
        "question_id": question["id"],
        "transcript": transcript,
        "transcript_segments": transcript_segments,
        "audio_duration_seconds": audio_duration_seconds,
        "audio_storage_path": audio_storage_path,
        "analysis_ability_score": llm_output.analysis_ability.score,
        "analysis_ability_reasoning": llm_output.analysis_ability.reasoning,
        "organization_coordination_score": llm_output.organization_coordination.score,
        "organization_coordination_reasoning": llm_output.organization_coordination.reasoning,
        "emergency_response_score": llm_output.emergency_response.score,
        "emergency_response_reasoning": llm_output.emergency_response.reasoning,
        "interpersonal_communication_score": llm_output.interpersonal_communication.score,
        "interpersonal_communication_reasoning": llm_output.interpersonal_communication.reasoning,
        "language_expression_score": llm_output.language_expression.score,
        "language_expression_reasoning": llm_output.language_expression.reasoning,
        "job_matching_score": llm_output.job_matching.score,
        "job_matching_reasoning": llm_output.job_matching.reasoning,
        "paralinguistic_fluency_score": paralinguistic_fluency_score,
        "structural_framework_check": llm_output.structural_framework_check.model_dump(),
        "improvement_suggestions": llm_output.improvement_suggestions,
        "model_ideal_answer": llm_output.model_ideal_answer,
        "rule_violations": llm_output.rule_violations,
        "anti_template_warning": anti_template_warning,
        "final_score": final_score,
        "created_at": datetime.now(UTC).isoformat(),
    }


async def _persist_record(request: Request, payload: dict[str, Any], client_request_id: str | None) -> dict[str, Any]:
    if client_request_id is not None:
        payload["client_request_id"] = client_request_id

    supabase = getattr(request.app.state, "supabase", None)
    if supabase is not None:
        try:
            result = await supabase.table("evaluations").insert(payload).execute()  # type: ignore[attr-defined]
            if getattr(result, "data", None):
                return result.data[0]
        except Exception:
            pass

    # Local fallback persistence for development and tests.
    store = getattr(request.app.state, "evaluations", None)
    if store is None:
        store = []
        request.app.state.evaluations = store

    if client_request_id is not None:
        for record in store:
            if record.get("client_request_id") == client_request_id:
                return record
    store.append(payload)
    return payload


async def run_evaluation_pipeline(
    *,
    request: Request,
    current_user: dict[str, Any],
    audio: UploadFile,
    question_id: str,
    client_request_id: str | None = None,
) -> dict[str, Any]:
    # 1. read and validate audio
    audio_bytes = await audio.read()
    validate_audio(audio_bytes, audio.content_type or "")

    # 2. question lookup
    question = _find_question(request, question_id)
    if question is None:
        raise HTTPException(status_code=400, detail={"error_code": "ERR_QUESTION_NOT_FOUND"})

    # 3. transcode
    wav_bytes = await transcode_to_wav(audio_bytes)

    # 4. ASR
    groq_client = getattr(request.app.state, "groq", None)
    if groq_client is None:
        asr_result = {
            "transcript": "",
            "transcript_segments": [],
            "audio_duration_seconds": 0.0,
        }
    else:
        asr_result = await run_asr(
            audio_wav_bytes=wav_bytes,
            question_type=question["question_type"],
            groq_client=groq_client,
            keyword_dict=getattr(request.app.state, "keyword_dict", {}),
        )

    transcript = asr_result["transcript"]
    transcript_segments = asr_result["transcript_segments"]

    # 5. vocab analysis
    vocab_result = analyze_vocab(
        transcript=transcript,
        question_type=question["question_type"],
        keyword_dict=getattr(request.app.state, "keyword_dict", {}),
    )

    # 6. anti-template warning
    anti_template_warning = check_anti_template(
        transcript=transcript,
        patterns=getattr(request.app.state, "cliche_patterns", []),
    )

    # 7. parallel LLM + storage upload
    llm_task = asyncio.create_task(
        _run_llm_or_fallback(
            request=request,
            transcript=transcript,
            question=question,
            policy_coverage=vocab_result["policy_coverage"],
            cliche_count=vocab_result["cliche_count"],
        )
    )
    upload_task = asyncio.create_task(
        _upload_to_storage(request=request, user_id=current_user["id"], audio_bytes=wav_bytes)
    )
    llm_output, storage_path = await asyncio.gather(llm_task, upload_task)

    # 8. rule caps
    capped_output = apply_rule_caps(
        llm_output=llm_output,
        transcript=transcript,
        question_type=question["question_type"],
    )

    # 9. fluency
    fluency_score = calculate_fluency_score(
        segments=transcript_segments,
        transcript=transcript,
        audio_duration_seconds=float(asr_result["audio_duration_seconds"] or 0.0),
    )

    result = InterviewResult(llm_output=capped_output, paralinguistic_fluency_score=fluency_score)
    payload = _build_response_payload(
        record_id=str(uuid4()),
        user_id=current_user["id"],
        question=question,
        transcript=transcript,
        transcript_segments=transcript_segments,
        audio_duration_seconds=float(asr_result["audio_duration_seconds"] or 0.0),
        audio_storage_path=storage_path,
        llm_output=capped_output,
        anti_template_warning=anti_template_warning,
        paralinguistic_fluency_score=fluency_score,
        final_score=result.final_score(),
    )

    # 10. persist
    stored = await _persist_record(request=request, payload=payload, client_request_id=client_request_id)
    return stored

