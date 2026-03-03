from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

MAX_AUDIO_SIZE = 10 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {"audio/webm", "audio/mp4", "video/webm", "video/mp4"}


class AudioValidationError(Exception):
    def __init__(self, message: str, error_code: str) -> None:
        self.message = message
        self.error_code = error_code
        super().__init__(message)


def _normalize_content_type(content_type: str) -> str:
    return content_type.split(";", 1)[0].strip().lower()


def _magic_check_fallback(payload: bytes, content_type: str) -> bool:
    if content_type in {"audio/webm", "video/webm"}:
        return payload.startswith(b"\x1A\x45\xDF\xA3")
    if content_type in {"audio/mp4", "video/mp4"}:
        return len(payload) >= 8 and payload[4:8] == b"ftyp"
    return False


def validate_audio(content: bytes, content_type: str) -> None:
    normalized_type = _normalize_content_type(content_type)
    if normalized_type not in ALLOWED_CONTENT_TYPES:
        raise AudioValidationError("Unsupported audio content type.", "ERR_INVALID_AUDIO")
    if len(content) > MAX_AUDIO_SIZE:
        raise AudioValidationError("Audio file exceeds 10MB limit.", "ERR_FILE_TOO_LARGE")

    try:
        import magic  # type: ignore

        mime = magic.from_buffer(content, mime=True)
        if mime not in {"video/webm", "audio/webm", "video/mp4", "audio/mp4", "application/octet-stream"}:
            raise AudioValidationError("Invalid audio magic header.", "ERR_INVALID_AUDIO")
    except ImportError:
        if not _magic_check_fallback(content, normalized_type):
            raise AudioValidationError("Invalid audio magic header.", "ERR_INVALID_AUDIO")


async def transcode_to_wav(input_bytes: bytes) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".input", delete=False) as src:
        src.write(input_bytes)
        src_path = Path(src.name)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as dst:
        dst_path = Path(dst.name)

    try:
        process = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-y",
            "-i",
            str(src_path),
            "-ar",
            "16000",
            "-ac",
            "1",
            "-f",
            "wav",
            str(dst_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise AudioValidationError(
                f"ffmpeg transcode failed: {stderr.decode(errors='ignore')}",
                "ERR_INVALID_AUDIO",
            )
        return dst_path.read_bytes()
    finally:
        if src_path.exists():
            src_path.unlink()
        if dst_path.exists():
            dst_path.unlink()
