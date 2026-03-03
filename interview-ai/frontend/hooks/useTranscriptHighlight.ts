import { useEffect, useRef, useState, type RefObject } from "react";

export interface TranscriptSegmentLite {
  text: string;
  start: number;
  end: number;
}

export function findActiveSegmentIndex(
  currentTime: number,
  segments: TranscriptSegmentLite[],
  toleranceSeconds = 0.5,
): number {
  for (let index = 0; index < segments.length; index += 1) {
    const segment = segments[index];
    if (currentTime >= segment.start && currentTime <= segment.end) {
      return index;
    }
  }

  for (let index = 0; index < segments.length; index += 1) {
    const segment = segments[index];
    if (currentTime >= segment.start - toleranceSeconds && currentTime <= segment.end + toleranceSeconds) {
      return index;
    }
  }
  return -1;
}

export function useTranscriptHighlight(
  audioRef: RefObject<HTMLAudioElement>,
  segments: TranscriptSegmentLite[],
  toleranceSeconds = 0.5,
) {
  const [activeIndex, setActiveIndex] = useState(-1);
  const frameRef = useRef<number | null>(null);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || segments.length === 0) {
      setActiveIndex(-1);
      return;
    }

    const cancelCurrentFrame = () => {
      if (frameRef.current !== null) {
        cancelAnimationFrame(frameRef.current);
        frameRef.current = null;
      }
    };

    const syncCurrentPosition = () => {
      const index = findActiveSegmentIndex(audio.currentTime, segments, toleranceSeconds);
      setActiveIndex((prev) => (prev === index ? prev : index));
    };

    const tick = () => {
      syncCurrentPosition();
      if (!audio.paused && !audio.ended) {
        frameRef.current = requestAnimationFrame(tick);
      } else {
        frameRef.current = null;
      }
    };

    const startRafLoop = () => {
      cancelCurrentFrame();
      frameRef.current = requestAnimationFrame(tick);
    };

    const stopRafLoop = () => {
      cancelCurrentFrame();
    };

    const handleSeeked = () => {
      syncCurrentPosition();
      if (!audio.paused && !audio.ended) {
        startRafLoop();
      }
    };

    audio.addEventListener("play", startRafLoop);
    audio.addEventListener("pause", stopRafLoop);
    audio.addEventListener("ended", stopRafLoop);
    audio.addEventListener("seeked", handleSeeked);

    syncCurrentPosition();

    return () => {
      cancelCurrentFrame();
      audio.removeEventListener("play", startRafLoop);
      audio.removeEventListener("pause", stopRafLoop);
      audio.removeEventListener("ended", stopRafLoop);
      audio.removeEventListener("seeked", handleSeeked);
    };
  }, [audioRef, segments, toleranceSeconds]);

  return { activeIndex };
}
