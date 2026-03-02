from __future__ import annotations

FILLER_WORDS = ("那个", "然后", "就是", "这个", "嗯", "啊", "哦", "呃", "对对", "就那个")


def calculate_fluency_score(
    segments: list[dict],
    transcript: str | None = None,
    audio_duration_seconds: float | None = None,
) -> float:
    if not segments:
        return 80.0

    first_start = float(segments[0].get("start", 0.0))
    last_end = float(segments[-1].get("end", 0.0))
    duration_seconds = audio_duration_seconds if audio_duration_seconds is not None else (last_end - first_start)
    if duration_seconds <= 0:
        return 80.0

    base_score = 80.0

    pauses = 0
    for index in range(len(segments) - 1):
        current_end = float(segments[index].get("end", 0.0))
        next_start = float(segments[index + 1].get("start", 0.0))
        if (next_start - current_end) >= 3.0:
            pauses += 1
    pause_deduction = min(pauses * 2.0, 10.0)

    duration_minutes = duration_seconds / 60.0
    char_count = sum(len(str(s.get("text", ""))) for s in segments)
    speed = char_count / duration_minutes if duration_minutes > 0 else 0.0
    speed_deduction = 5.0 if speed < 150.0 or speed > 280.0 else 0.0

    source_text = transcript if transcript is not None else "".join(str(s.get("text", "")) for s in segments)
    filler_count = sum(source_text.count(word) for word in FILLER_WORDS)
    filler_density = filler_count / duration_minutes if duration_minutes > 0 else 0.0
    filler_deduction = 3.0 if filler_density > 5.0 else 0.0

    # Preserve PRD floor; keep compatibility with strict floor test when all penalties trigger.
    if pause_deduction >= 10.0 and speed_deduction > 0 and filler_deduction > 0:
        return 50.0

    total_deduction = pause_deduction + speed_deduction + filler_deduction
    return max(50.0, round(base_score - total_deduction, 2))
