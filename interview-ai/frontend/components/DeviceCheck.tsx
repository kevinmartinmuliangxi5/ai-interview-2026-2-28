"use client";

import { useEffect, useRef, useState } from "react";

type MicStatus = "pending" | "granted" | "denied";

interface DeviceCheckProps {
  onReady: () => void;
}

export function DeviceCheck({ onReady }: DeviceCheckProps) {
  const [micStatus, setMicStatus] = useState<MicStatus>("pending");
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const animationRef = useRef<number | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);

  useEffect(() => {
    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      setMicStatus("denied");
      return;
    }

    let cancelled = false;
    navigator.mediaDevices
      .getUserMedia({ audio: true, video: false })
      .then((stream) => {
        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }
        streamRef.current = stream;
        setMicStatus("granted");

        const audioContext = new AudioContext();
        const analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        const source = audioContext.createMediaStreamSource(stream);
        source.connect(analyser);
        audioContextRef.current = audioContext;

        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        const canvas = canvasRef.current;
        const ctx = canvas?.getContext("2d");
        if (!canvas || !ctx) {
          return;
        }

        const draw = () => {
          analyser.getByteFrequencyData(dataArray);
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          ctx.fillStyle = "#eff6ff";
          ctx.fillRect(0, 0, canvas.width, canvas.height);
          const barWidth = canvas.width / bufferLength;
          let x = 0;
          for (let i = 0; i < bufferLength; i += 1) {
            const barHeight = (dataArray[i] / 255) * canvas.height;
            ctx.fillStyle = "#2563eb";
            ctx.fillRect(x, canvas.height - barHeight, Math.max(1, barWidth - 1), barHeight);
            x += barWidth;
          }
          animationRef.current = requestAnimationFrame(draw);
        };

        draw();
      })
      .catch((error: DOMException) => {
        if (error.name === "NotAllowedError" || error.name === "PermissionDeniedError") {
          setMicStatus("denied");
          return;
        }
        setMicStatus("denied");
      });

    return () => {
      cancelled = true;
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
      streamRef.current?.getTracks().forEach((track) => track.stop());
      audioContextRef.current?.close();
    };
  }, []);

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6">
      <h2 className="text-lg font-semibold text-slate-900">设备检测</h2>
      <p className="mt-1 text-sm text-slate-600">请授权麦克风后进入考场。</p>

      <canvas
        ref={canvasRef}
        width={640}
        height={120}
        className="mt-4 h-24 w-full rounded-xl border border-slate-200 bg-blue-50"
      />

      {micStatus === "denied" ? (
        <p data-testid="mic-error" className="mt-3 text-sm text-red-600">
          麦克风权限被拒绝，请在浏览器设置中允许访问。
        </p>
      ) : null}

      <button
        type="button"
        onClick={onReady}
        disabled={micStatus !== "granted"}
        className="min-h-12 min-w-12 mt-5 rounded-xl bg-blue-600 px-4 py-3 text-white disabled:cursor-not-allowed disabled:opacity-50"
      >
        进入考场
      </button>
    </section>
  );
}
