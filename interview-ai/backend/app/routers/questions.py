from __future__ import annotations

import random
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/api/v1/questions", tags=["questions"])


@router.get("/draw")
async def draw_questions(
    request: Request,
    count: int = Query(default=3, ge=3, le=5),
    _current_user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    questions = getattr(request.app.state, "questions", [])
    if not questions:
        raise HTTPException(status_code=500, detail={"error_code": "ERR_INTERNAL"})
    if len(questions) <= count:
        return questions
    return random.sample(questions, count)


@router.get("/{question_id}")
async def get_question(
    question_id: str,
    request: Request,
    _current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    questions = getattr(request.app.state, "questions", [])
    for question in questions:
        if question.get("id") == question_id:
            return question
    raise HTTPException(status_code=404, detail={"error_code": "ERR_NOT_FOUND"})

