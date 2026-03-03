from __future__ import annotations

import asyncio
from typing import Any


class ASRTimeoutError(Exception):
    def __init__(self, message: str = "ASR service unavailable after retries.") -> None:
        super().__init__(message)


def _obj_get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _extract_segments(response: Any) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []

    words = _obj_get(response, "words", None) or []
    for word in words:
        text = _obj_get(word, "word", None) or _obj_get(word, "text", "")
        if not text:
            continue
        start = _to_float(_obj_get(word, "start", 0.0))
        end = _to_float(_obj_get(word, "end", start))
        segments.append({"text": str(text), "start": start, "end": end})

    if segments:
        return segments

    raw_segments = _obj_get(response, "segments", None) or []
    for segment in raw_segments:
        text = _obj_get(segment, "text", "")
        if not text:
            continue
        start = _to_float(_obj_get(segment, "start", 0.0))
        end = _to_float(_obj_get(segment, "end", start))
        segments.append({"text": str(text), "start": start, "end": end})

    if segments:
        return segments

    text = str(_obj_get(response, "text", "") or "")
    if not text:
        return []
    duration = _to_float(_obj_get(response, "duration", 0.0))
    return [{"text": text, "start": 0.0, "end": duration}]


async def run_asr(
    audio_wav_bytes: bytes,
    question_type: str,
    groq_client: Any,
    keyword_dict: dict[str, list[str]],
) -> dict[str, Any]:
    top_keywords = keyword_dict.get(question_type, [])[:20]
    prompt = "，".join(top_keywords)

    last_error: Exception | None = None
    for attempt in range(3):  # initial + 2 retries
        try:
            response = await groq_client.audio.transcriptions.create(
                file=("audio.wav", audio_wav_bytes),
                model="whisper-large-v3",
                response_format="verbose_json",
                language="zh",
                prompt=prompt,
                temperature=0.0,
            )

            segments = _extract_segments(response)
            transcript = str(_obj_get(response, "text", "") or "")
            if not transcript:
                transcript = "".join(segment["text"] for segment in segments)
            return {
                "transcript": transcript,
                "transcript_segments": segments,
                "audio_duration_seconds": _to_float(_obj_get(response, "duration", 0.0)),
            }
        except Exception as exc:  # pragma: no cover - covered by retry tests
            last_error = exc
            if attempt == 2:
                break
            await asyncio.sleep(2**attempt)

    raise ASRTimeoutError(str(last_error) if last_error else "ASR failed without error context.")
