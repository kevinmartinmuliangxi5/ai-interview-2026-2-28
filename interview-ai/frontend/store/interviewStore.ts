import { create } from "zustand";

export const INTERVIEW_STATES = [
  "IDLE",
  "READING",
  "RECORDING",
  "PROCESSING",
  "REVIEW",
] as const;

export type InterviewState = (typeof INTERVIEW_STATES)[number];

export interface InterviewQuestion {
  id: string;
  content: string;
  question_type: string;
  time_limit_seconds: number;
}

interface InterviewStoreState {
  questions: InterviewQuestion[];
  currentQuestionIndex: number;
  state: InterviewState;
  setQuestions: (questions: InterviewQuestion[]) => void;
  setState: (next: InterviewState) => void;
  nextQuestion: () => void;
  reset: () => void;
}

export const useInterviewStore = create<InterviewStoreState>((set) => ({
  questions: [],
  currentQuestionIndex: 0,
  state: "IDLE",
  setQuestions: (questions) =>
    set({
      questions,
      currentQuestionIndex: 0,
      state: "READING",
    }),
  setState: (state) => set({ state }),
  nextQuestion: () =>
    set((state) => ({
      currentQuestionIndex: state.currentQuestionIndex + 1,
      state: "READING",
    })),
  reset: () =>
    set({
      questions: [],
      currentQuestionIndex: 0,
      state: "IDLE",
    }),
}));
