"use client";

import { useEffect, useMemo, useRef } from "react";

import { useTranscriptHighlight } from "@/hooks/useTranscriptHighlight";
import type { TranscriptSegment } from "@/types/evaluation";

interface AudioTranscriptSyncProps {
  audioSrc: string | null;
  segments: TranscriptSegment[];
}

export function AudioTranscriptSync({ audioSrc, segments }: AudioTranscriptSyncProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const lineRefs = useRef<Array<HTMLParagraphElement | null>>([]);
  const { activeIndex } = useTranscriptHighlight(audioRef, segments);
  const playableAudioSrc = useMemo(() => {
    if (!audioSrc) {
      return null;
    }
    return audioSrc.startsWith("http://") || audioSrc.startsWith("https://") ? audioSrc : null;
  }, [audioSrc]);

  useEffect(() => {
    if (activeIndex < 0) {
      return;
    }
    lineRefs.current[activeIndex]?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [activeIndex]);

  return (
    <section className="rounded-xl border border-slate-200 p-4">
      <h2 className="text-lg font-semibold text-slate-900">音频与转写同步</h2>
      {playableAudioSrc ? (
        <audio ref={audioRef} controls className="mt-3 w-full" src={playableAudioSrc}>
          浏览器暂不支持音频播放。
        </audio>
      ) : (
        <div className="mt-3 rounded-lg border border-dashed border-slate-300 bg-slate-50 p-3 text-sm text-slate-500">
          当前环境未提供可播放音频链接，仅展示转写文本。
        </div>
      )}

      <div className="mt-4 max-h-80 space-y-2 overflow-y-auto rounded-lg bg-slate-50 p-3">
        {segments.length === 0 ? (
          <p className="text-sm text-slate-500">暂无转写片段。</p>
        ) : (
          segments.map((segment, index) => (
            <p
              key={`${segment.start}-${segment.end}-${index}`}
              ref={(node) => {
                lineRefs.current[index] = node;
              }}
              className={`rounded-md px-2 py-1 text-sm leading-6 transition ${
                activeIndex === index ? "bg-amber-100 text-slate-900" : "text-slate-600"
              }`}
            >
              <span className="mr-2 text-xs text-slate-400">
                {segment.start.toFixed(1)}s - {segment.end.toFixed(1)}s
              </span>
              {segment.text}
            </p>
          ))
        )}
      </div>
    </section>
  );
}
