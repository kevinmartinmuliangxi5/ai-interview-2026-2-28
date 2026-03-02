from __future__ import annotations

import pytest

from app.services.audio_processor import AudioValidationError, validate_audio


def test_invalid_content_type_raises_err_invalid_audio() -> None:
    with pytest.raises(AudioValidationError) as exc:
        validate_audio(b'123', 'text/plain')
    assert exc.value.error_code == 'ERR_INVALID_AUDIO'


def test_file_too_large_raises_err_file_too_large() -> None:
    payload = b'0' * (10 * 1024 * 1024 + 1)
    with pytest.raises(AudioValidationError) as exc:
        validate_audio(payload, 'audio/webm')
    assert exc.value.error_code == 'ERR_FILE_TOO_LARGE'


def test_valid_payload_passes_basic_checks() -> None:
    payload = b'\x1a\x45\xdf\xa3' + b'0' * 100
    validate_audio(payload, 'audio/webm')
