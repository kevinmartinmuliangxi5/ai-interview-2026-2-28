"use client";

import { useCallback, useRef } from "react";

const MIME_CANDIDATES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/mp4;codecs=mp4a.40.2",
  "audio/mp4",
] as const;

function getSupportedMimeType() {
  if (typeof MediaRecorder === "undefined") {
    return "";
  }
  return MIME_CANDIDATES.find((mime) => MediaRecorder.isTypeSupported(mime)) ?? "";
}

export function useAudioRecorder() {
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const mimeTypeRef = useRef(getSupportedMimeType());

  const startRecording = useCallback(async (stream: MediaStream) => {
    chunksRef.current = [];
    const options: MediaRecorderOptions = {};
    if (mimeTypeRef.current) {
      options.mimeType = mimeTypeRef.current;
    }

    const recorder = new MediaRecorder(stream, options);
    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        chunksRef.current.push(event.data);
      }
    };
    recorder.start(10_000);
    recorderRef.current = recorder;
  }, []);

  const stopRecording = useCallback(() => {
    return new Promise<Blob>((resolve, reject) => {
      const recorder = recorderRef.current;
      if (!recorder) {
        reject(new Error("Recorder is not started."));
        return;
      }

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, {
          type: mimeTypeRef.current || "audio/webm",
        });
        resolve(blob);
      };
      recorder.stop();
    });
  }, []);

  return {
    startRecording,
    stopRecording,
    mimeType: mimeTypeRef.current || "audio/webm",
  };
}
