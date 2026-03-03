"use client";

import { useRef } from "react";

import { type InterviewQuestion, useInterviewStore } from "@/store/interviewStore";

type Submitter = (payload: {
  questions: InterviewQuestion[];
  audioBlobs: Map<number, Blob>;
}) => Promise<void>;

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

export function useInterviewFlowManager() {
  const questions = useInterviewStore((store) => store.questions);
  const currentQuestionIndex = useInterviewStore((store) => store.currentQuestionIndex);
  const state = useInterviewStore((store) => store.state);
  const setQuestions = useInterviewStore((store) => store.setQuestions);
  const setState = useInterviewStore((store) => store.setState);
  const moveToNextQuestion = useInterviewStore((store) => store.nextQuestion);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const audioBlobsRef = useRef<Map<number, Blob>>(new Map());

  function startExam(examQuestions: InterviewQuestion[]) {
    setQuestions(examQuestions);
  }

  function startRecording(stream: MediaStream) {
    const snapshot = useInterviewStore.getState();
    if (snapshot.state !== "READING") {
      return;
    }

    chunksRef.current = [];
    const mimeType = getSupportedMimeType();
    const options: MediaRecorderOptions = mimeType ? { mimeType } : {};
    const recorder = new MediaRecorder(stream, options);
    recorder.ondataavailable = (event: BlobEvent) => {
      if (event.data.size > 0) {
        chunksRef.current.push(event.data);
      }
    };
    recorder.start(10_000);
    recorderRef.current = recorder;
    setState("RECORDING");
  }

  function stopCurrentRecording() {
    return new Promise<Blob | null>((resolve) => {
      const recorder = recorderRef.current;
      if (!recorder || recorder.state === "inactive") {
        resolve(null);
        return;
      }

      recorder.onstop = () => {
        const mimeType = recorder.mimeType || "audio/webm";
        const blob = new Blob(chunksRef.current, { type: mimeType });
        const snapshot = useInterviewStore.getState();
        audioBlobsRef.current.set(snapshot.currentQuestionIndex, blob);
        resolve(blob);
      };
      recorder.stop();
    });
  }

  function nextQuestion() {
    const snapshot = useInterviewStore.getState();
    const isLastQuestion = snapshot.currentQuestionIndex >= snapshot.questions.length - 1;
    if (isLastQuestion) {
      setState("PROCESSING");
      return;
    }
    moveToNextQuestion();
  }

  async function submitAll(submitter?: Submitter) {
    setState("PROCESSING");
    if (submitter) {
      const snapshot = useInterviewStore.getState();
      await submitter({
        questions: snapshot.questions,
        audioBlobs: audioBlobsRef.current,
      });
      setState("REVIEW");
    }
  }

  return {
    questions,
    currentQuestionIndex,
    state,
    startExam,
    startRecording,
    stopCurrentRecording,
    nextQuestion,
    submitAll,
    audioBlobsRef,
  };
}
