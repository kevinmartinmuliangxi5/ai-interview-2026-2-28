from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from app.dependencies.auth import get_current_user
from app.middleware.rate_limit import limiter
from app.services.asr import ASRTimeoutError
from app.services.audio_processor import AudioValidationError
from app.services.evaluation_pipeline import run_evaluation_pipeline
from app.services.llm_evaluator import LLMParseError

router = APIRouter(prefix="/api/v1/evaluations", tags=["evaluations"])


async def _load_evaluation_from_supabase(
    request: Request,
    evaluation_id: str,
    user_id: str,
) -> dict[str, Any] | None:
    supabase = getattr(request.app.state, "supabase", None)
    if supabase is None:
        return None

    try:
        result = (
            await supabase.table("evaluations")
            .select("*")
            .eq("id", evaluation_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
    except Exception:
        return None

    data = getattr(result, "data", None) or []
    return data[0] if data else None


def _load_evaluation_from_local_store(
    request: Request,
    evaluation_id: str,
    user_id: str,
) -> dict[str, Any] | None:
    records = getattr(request.app.state, "evaluations", [])
    for record in reversed(records):
        if record.get("id") == evaluation_id and record.get("user_id") == user_id:
            return record
    return None


@router.post("/submit")
@limiter.limit("3/minute")
async def submit_evaluation(
    request: Request,
    audio: UploadFile = File(...),
    question_id: str = Form(...),
    client_request_id: str | None = Form(default=None),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> JSONResponse:
    try:
        result = await run_evaluation_pipeline(
            request=request,
            current_user=current_user,
            audio=audio,
            question_id=question_id,
            client_request_id=client_request_id,
        )
        return JSONResponse(status_code=201, content=result)
    except AudioValidationError as exc:
        status_code = 413 if exc.error_code == "ERR_FILE_TOO_LARGE" else 400
        raise HTTPException(status_code=status_code, detail={"error_code": exc.error_code, "message": exc.message})
    except (ASRTimeoutError, LLMParseError) as exc:
        code = "ERR_ASR_TIMEOUT" if isinstance(exc, ASRTimeoutError) else "ERR_LLM_PARSE_FAILED"
        raise HTTPException(status_code=503, detail={"error_code": code, "message": str(exc)})


@router.get("/{evaluation_id}")
async def get_evaluation(
    evaluation_id: str,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> JSONResponse:
    user_id = str(current_user["id"])
    record = await _load_evaluation_from_supabase(request, evaluation_id, user_id)
    if record is None:
        record = _load_evaluation_from_local_store(request, evaluation_id, user_id)

    if record is None:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "ERR_NOT_FOUND", "message": "评估记录不存在。"},
        )

    return JSONResponse(status_code=200, content=record)
