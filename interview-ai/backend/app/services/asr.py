from __future__ import annotations

import asyncio
from typing import Any


class ASRTimeoutError(Exception):
    def __init__(self, message: str = "ASR service unavailable after retries.") -> None:
        super().__init__(message)


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

            segments = [
                {"text": w.word, "start": float(w.start), "end": float(w.end)}
                for w in (response.words or [])
            ]
            return {
                "transcript": str(response.text or ""),
                "transcript_segments": segments,
                "audio_duration_seconds": float(response.duration or 0.0),
            }
        except Exception as exc:  # pragma: no cover - covered by retry tests
            last_error = exc
            if attempt == 2:
                break
            await asyncio.sleep(2**attempt)

    raise ASRTimeoutError(str(last_error) if last_error else "ASR failed without error context.")

