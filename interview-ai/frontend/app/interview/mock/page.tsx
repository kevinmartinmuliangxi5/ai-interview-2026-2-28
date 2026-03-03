"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { NetworkRetryBanner } from "@/components/NetworkRetryBanner";
import { ProcessingSkeleton } from "@/components/ProcessingSkeleton";
import { useAudioRecorder } from "@/hooks/useAudioRecorder";
import { useInterviewFlowManager } from "@/hooks/useInterviewFlowManager";
import { useInterviewTimer } from "@/hooks/useInterviewTimer";
import { useRequireAuth } from "@/lib/auth";
import { type InterviewQuestion } from "@/store/interviewStore";

const MOCK_QUESTIONS: InterviewQuestion[] = [
  {
    id: "4f3af2b0-9e8f-48fe-8d05-8f52332f1001",
    question_type: "COMPREHENSIVE_ANALYSIS",
    content: "当前部分基层单位在接诉即办中存在重接诉轻办诉的问题。请谈谈你的看法。",
    time_limit_seconds: 180,
  },
  {
    id: "4f3af2b0-9e8f-48fe-8d05-8f52332f3001",
    question_type: "EMERGENCY_RESPONSE",
    content: "社区突发停水，居民情绪激动并传播不实信息，你会如何处置？",
    time_limit_seconds: 180,
  },
];

interface PendingUpload {
  blob: Blob;
  questionId: string;
  clientRequestId: string;
}

export default function InterviewMockPage() {
  useRequireAuth();

  const router = useRouter();
  const initializedRef = useRef(false);
  const streamRef = useRef<MediaStream | null>(null);

  const flow = useInterviewFlowManager();
  const recorder = useAudioRecorder();
  const [pendingUpload, setPendingUpload] = useState<PendingUpload | null>(null);
  const [uploadErrorMessage, setUploadErrorMessage] = useState("");

  const currentQuestion = flow.questions[flow.currentQuestionIndex];
  const isLastQuestion = useMemo(
    () => flow.currentQuestionIndex >= flow.questions.length - 1,
    [flow.currentQuestionIndex, flow.questions.length],
  );

  useEffect(() => {
    if (initializedRef.current) {
      return;
    }
    flow.startExam(MOCK_QUESTIONS);
    initializedRef.current = true;
  }, [flow]);

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  const readingTimer = useInterviewTimer(flow.state === "READING" ? 60 : 0, () => {});
  const recordingTimer = useInterviewTimer(
    flow.state === "RECORDING" ? currentQuestion?.time_limit_seconds ?? 0 : 0,
    () => {
      void handleStopRecording();
    },
  );

  async function submitPending(payload: PendingUpload) {
    const token = window.sessionStorage.getItem("access_token");
    if (!token) {
      router.replace("/login");
      return;
    }

    const formData = new FormData();
    formData.append("audio", payload.blob, "recording.webm");
    formData.append("question_id", payload.questionId);
    formData.append("client_request_id", payload.clientRequestId);

    const response = await fetch("/api/evaluations", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });

    const data = await response.json();
    if (!response.ok) {
      const detail = data?.detail;
      const backendMessage =
        detail?.message ?? detail?.error_code ?? data?.message ?? data?.error_code ?? "提交失败";
      throw new Error(backendMessage);
    }

    setPendingUpload(null);
    setUploadErrorMessage("");
    router.push(`/review/${data.id}`);
  }

  async function handleStartRecording() {
    if (flow.state !== "READING") {
      return;
    }

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    streamRef.current = stream;
    await recorder.startRecording(stream);
    flow.startRecording();
  }

  async function handleStopRecording() {
    if (flow.state !== "RECORDING" || !currentQuestion) {
      return;
    }

    const blob = await recorder.stopRecording();
    flow.setBlobForCurrentQuestion(blob);
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;

    if (!isLastQuestion) {
      flow.nextQuestion();
      return;
    }

    flow.nextQuestion();
    const payload: PendingUpload = {
      blob,
      questionId: currentQuestion.id,
      clientRequestId: crypto.randomUUID(),
    };
    setPendingUpload(payload);

    try {
      await submitPending(payload);
    } catch (error) {
      const message = error instanceof Error ? error.message : "提交失败，请重试。";
      setUploadErrorMessage(message);
    }
  }

  async function handleRetryUpload() {
    if (!pendingUpload) {
      return;
    }
    try {
      await submitPending(pendingUpload);
    } catch (error) {
      const message = error instanceof Error ? error.message : "提交失败，请重试。";
      setUploadErrorMessage(message);
    }
  }

  if (!currentQuestion) {
    return (
      <main className="min-h-screen bg-slate-100 p-8">
        <p className="text-slate-600">题目加载中...</p>
      </main>
    );
  }

  if (flow.state === "PROCESSING") {
    return (
      <main className="min-h-screen bg-slate-100 p-4">
        <ProcessingSkeleton />
        <div className="mx-auto mt-4 max-w-3xl">
          <NetworkRetryBanner
            visible={Boolean(uploadErrorMessage)}
            message={uploadErrorMessage}
            onRetry={handleRetryUpload}
          />
        </div>
      </main>
    );
  }

  if (flow.state === "RECORDING") {
    return (
      <main className="min-h-screen bg-slate-100 px-4 py-8">
        <section className="mx-auto max-w-4xl rounded-2xl bg-white p-8 shadow-sm">
          <header className="flex items-center justify-between">
            <h1 className="text-xl font-semibold text-slate-900">作答中</h1>
            <div
              data-testid="recording-indicator"
              className="inline-flex items-center gap-2 rounded-full bg-red-50 px-3 py-1 text-sm text-red-600"
            >
              <span className="h-2 w-2 animate-pulse rounded-full bg-red-600" />
              录制中
            </div>
          </header>
          <p className="mt-4 text-slate-800">{currentQuestion.content}</p>
          <p className="mt-6 text-sm text-slate-500">
            剩余作答时间：{Math.max(0, recordingTimer.secondsLeft)} 秒
          </p>
          <p className="mt-2 text-sm text-slate-400">录音格式：{recorder.mimeType}</p>
          <button
            type="button"
            onClick={() => void handleStopRecording()}
            className="min-h-12 min-w-12 mt-6 rounded-xl bg-blue-600 px-4 py-3 text-white"
          >
            作答结束
          </button>
        </section>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-100 px-4 py-8">
      <section className="mx-auto max-w-4xl rounded-2xl bg-white p-8 shadow-sm">
        <p className="text-sm text-slate-500">
          第 {flow.currentQuestionIndex + 1} / {flow.questions.length} 题
        </p>
        <h1 className="mt-3 text-2xl font-semibold text-slate-900">阅读题目并思考</h1>
        <p className="mt-6 text-lg leading-8 text-slate-800">{currentQuestion.content}</p>
        <p className="mt-6 text-sm text-slate-500">审题倒计时：{readingTimer.secondsLeft} 秒</p>
        <button
          type="button"
          onClick={() => void handleStartRecording()}
          className="min-h-12 min-w-12 mt-6 rounded-xl bg-blue-600 px-5 py-3 text-white"
        >
          思考完毕，开始作答
        </button>
      </section>
    </main>
  );
}
