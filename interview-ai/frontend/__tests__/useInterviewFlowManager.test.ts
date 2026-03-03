import { act, renderHook } from "@testing-library/react";

import { INTERVIEW_STATES, type InterviewQuestion, useInterviewStore } from "@/store/interviewStore";
import { useInterviewFlowManager } from "@/hooks/useInterviewFlowManager";

class MockMediaRecorder {
  static isTypeSupported() {
    return true;
  }

  ondataavailable: ((event: { data: Blob }) => void) | null = null;
  onstop: (() => void) | null = null;
  state: "inactive" | "recording" = "inactive";

  start() {
    this.state = "recording";
  }

  stop() {
    this.state = "inactive";
    this.ondataavailable?.({ data: new Blob(["audio"]) });
    this.onstop?.();
  }
}

const QUESTIONS: InterviewQuestion[] = [
  {
    id: "q1",
    content: "第一题",
    question_type: "COMPREHENSIVE_ANALYSIS",
    time_limit_seconds: 180,
  },
  {
    id: "q2",
    content: "第二题",
    question_type: "SELF_COGNITION",
    time_limit_seconds: 180,
  },
];

describe("useInterviewFlowManager", () => {
  beforeEach(() => {
    useInterviewStore.getState().reset();
    (global as unknown as { MediaRecorder: typeof MockMediaRecorder }).MediaRecorder = MockMediaRecorder;
  });

  it("初始状态为 IDLE", () => {
    renderHook(() => useInterviewFlowManager());
    expect(useInterviewStore.getState().state).toBe("IDLE");
  });

  it("startExam 后进入 READING", () => {
    const { result } = renderHook(() => useInterviewFlowManager());

    act(() => {
      result.current.startExam(QUESTIONS);
    });

    expect(useInterviewStore.getState().state).toBe("READING");
  });

  it("startRecording 后进入 RECORDING", () => {
    const { result } = renderHook(() => useInterviewFlowManager());

    act(() => {
      result.current.startExam(QUESTIONS);
    });
    act(() => {
      result.current.startRecording({} as MediaStream);
    });

    expect(useInterviewStore.getState().state).toBe("RECORDING");
  });

  it("非最后题 nextQuestion 后回到 READING", async () => {
    const { result } = renderHook(() => useInterviewFlowManager());

    act(() => {
      result.current.startExam(QUESTIONS);
      result.current.startRecording({} as MediaStream);
    });
    await act(async () => {
      await result.current.stopCurrentRecording();
      result.current.nextQuestion();
    });

    expect(useInterviewStore.getState().currentQuestionIndex).toBe(1);
    expect(useInterviewStore.getState().state).toBe("READING");
  });

  it("最后一题 nextQuestion 后进入 PROCESSING", async () => {
    const { result } = renderHook(() => useInterviewFlowManager());

    act(() => {
      result.current.startExam(QUESTIONS);
      result.current.startRecording({} as MediaStream);
    });
    await act(async () => {
      await result.current.stopCurrentRecording();
      result.current.nextQuestion();
      result.current.startRecording({} as MediaStream);
      await result.current.stopCurrentRecording();
      result.current.nextQuestion();
    });

    expect(useInterviewStore.getState().state).toBe("PROCESSING");
  });

  it("状态机不出现未定义中间态", async () => {
    const { result } = renderHook(() => useInterviewFlowManager());

    act(() => {
      result.current.startExam(QUESTIONS);
      result.current.startRecording({} as MediaStream);
    });
    await act(async () => {
      await result.current.stopCurrentRecording();
      result.current.nextQuestion();
      await result.current.submitAll(async () => Promise.resolve());
    });

    const currentState = useInterviewStore.getState().state;
    expect(INTERVIEW_STATES.includes(currentState)).toBe(true);
  });
});
