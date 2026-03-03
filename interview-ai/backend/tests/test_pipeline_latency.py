from __future__ import annotations

import asyncio
import time
from io import BytesIO
from types import SimpleNamespace
from typing import Any

import pytest
from starlette.datastructures import Headers, UploadFile

import app.services.evaluation_pipeline as evaluation_pipeline


def _make_request_state() -> SimpleNamespace:
    return SimpleNamespace(
        questions=[
            {
                "id": "q-latency-1",
                "question_type": "COMPREHENSIVE_ANALYSIS",
                "content": "请结合基层治理场景作答。",
            }
        ],
        keyword_dict={},
        cliche_patterns=[],
        question_cache={},
        evaluations=[],
        supabase=None,
        groq=object(),
        openai=object(),
    )


@pytest.mark.asyncio
async def test_pipeline_latency_mock_under_15s(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _make_request_state()
    request = SimpleNamespace(app=SimpleNamespace(state=state))
    audio = UploadFile(
        file=BytesIO(b"fake-webm"),
        filename="recording.webm",
        headers=Headers({"content-type": "audio/webm"}),
    )

    def fake_validate(_audio_bytes: bytes, _content_type: str) -> None:
        return None

    async def fake_transcode(_audio_bytes: bytes) -> bytes:
        return b"fake-wav"

    async def fake_asr(**_kwargs: Any) -> dict[str, Any]:
        return {
            "transcript": "这是用于延迟测试的转写文本。",
            "transcript_segments": [{"text": "这是用于延迟测试的转写文本。", "start": 0.0, "end": 1.0}],
            "audio_duration_seconds": 1.0,
        }

    async def fake_llm(**_kwargs: Any) -> Any:
        await asyncio.sleep(0.05)
        return evaluation_pipeline._default_llm_output()

    async def fake_upload(**_kwargs: Any) -> str:
        await asyncio.sleep(0.05)
        return "interview-audio/user-1/mock.wav"

    monkeypatch.setattr(evaluation_pipeline, "validate_audio", fake_validate)
    monkeypatch.setattr(evaluation_pipeline, "transcode_to_wav", fake_transcode)
    monkeypatch.setattr(evaluation_pipeline, "run_asr", fake_asr)
    monkeypatch.setattr(evaluation_pipeline, "_run_llm_or_fallback", fake_llm)
    monkeypatch.setattr(evaluation_pipeline, "_upload_to_storage", fake_upload)

    start = time.perf_counter()
    result = await evaluation_pipeline.run_evaluation_pipeline(
        request=request,
        current_user={"id": "user-1", "email": "user@example.com"},
        audio=audio,
        question_id="q-latency-1",
        client_request_id="4f3af2b0-9e8f-48fe-8d05-8f52332f9999",
    )
    elapsed = time.perf_counter() - start

    assert elapsed <= 15.0, f"Pipeline latency {elapsed:.2f}s exceeded 15s SLA"
    assert elapsed < 0.2, f"Mock pipeline expected parallel execution, got {elapsed:.3f}s"
    assert result.get("final_score") is not None
