from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.asr import ASRTimeoutError, run_asr



def _mock_groq_response() -> MagicMock:
    word = MagicMock()
    word.word = '各位考官'
    word.start = 0.0
    word.end = 0.8

    response = MagicMock()
    response.text = '各位考官，关于这个问题'
    response.words = [word]
    response.duration = 5.2
    return response


@pytest.mark.asyncio
async def test_run_asr_success_returns_segments() -> None:
    groq_client = MagicMock()
    groq_client.audio.transcriptions.create = AsyncMock(return_value=_mock_groq_response())

    result = await run_asr(
        audio_wav_bytes=b'fake-wav',
        question_type='COMPREHENSIVE_ANALYSIS',
        groq_client=groq_client,
        keyword_dict={'COMPREHENSIVE_ANALYSIS': ['接诉即办']},
    )

    assert result['transcript'] == '各位考官，关于这个问题'
    assert result['transcript_segments'][0] == {'text': '各位考官', 'start': 0.0, 'end': 0.8}


@pytest.mark.asyncio
async def test_prompt_injects_top20_keywords_only() -> None:
    groq_client = MagicMock()
    groq_client.audio.transcriptions.create = AsyncMock(return_value=_mock_groq_response())

    keywords = [f'词{i}' for i in range(30)]
    await run_asr(
        audio_wav_bytes=b'fake-wav',
        question_type='COMPREHENSIVE_ANALYSIS',
        groq_client=groq_client,
        keyword_dict={'COMPREHENSIVE_ANALYSIS': keywords},
    )

    kwargs = groq_client.audio.transcriptions.create.await_args.kwargs
    prompt = kwargs['prompt']
    assert len(prompt.split('，')) <= 20


@pytest.mark.asyncio
async def test_run_asr_retries_and_raises_timeout_error() -> None:
    groq_client = MagicMock()
    groq_client.audio.transcriptions.create = AsyncMock(side_effect=RuntimeError('upstream error'))

    with pytest.raises(ASRTimeoutError):
        await run_asr(
            audio_wav_bytes=b'fake-wav',
            question_type='COMPREHENSIVE_ANALYSIS',
            groq_client=groq_client,
            keyword_dict={'COMPREHENSIVE_ANALYSIS': ['接诉即办']},
        )
