import { act, renderHook } from "@testing-library/react";

import { useInterviewTimer } from "@/hooks/useInterviewTimer";

describe("useInterviewTimer", () => {
  let nowMs = 0;
  let nowSpy: jest.SpyInstance<number, []>;

  beforeEach(() => {
    jest.useFakeTimers();
    nowMs = 0;
    nowSpy = jest.spyOn(performance, "now").mockImplementation(() => nowMs);
    Object.defineProperty(document, "visibilityState", {
      value: "visible",
      configurable: true,
    });
  });

  afterEach(() => {
    nowSpy.mockRestore();
    jest.useRealTimers();
  });

  function tick(ms: number) {
    nowMs += ms;
    act(() => {
      jest.advanceTimersByTime(ms);
    });
  }

  it("初始秒数正确", () => {
    const onExpire = jest.fn();
    const { result } = renderHook(() => useInterviewTimer(180, onExpire));
    expect(result.current.secondsLeft).toBe(180);
    expect(result.current.isWarning).toBe(false);
  });

  it("三分钟漂移不超过1秒", () => {
    const onExpire = jest.fn();
    const { result } = renderHook(() => useInterviewTimer(180, onExpire));

    tick(179000);
    expect(result.current.secondsLeft).toBeGreaterThanOrEqual(1);
    expect(result.current.secondsLeft).toBeLessThanOrEqual(2);

    tick(1000);
    expect(result.current.secondsLeft).toBe(0);
    expect(onExpire).toHaveBeenCalledTimes(1);
  });

  it("visibilitychange 切回时会重算剩余时间", () => {
    const onExpire = jest.fn();
    const { result } = renderHook(() => useInterviewTimer(120, onExpire));

    nowMs += 45000;
    Object.defineProperty(document, "visibilityState", {
      value: "visible",
      configurable: true,
    });
    act(() => {
      document.dispatchEvent(new Event("visibilitychange"));
    });

    expect(result.current.secondsLeft).toBeGreaterThanOrEqual(75);
    expect(result.current.secondsLeft).toBeLessThanOrEqual(76);
  });

  it("剩余60秒内 isWarning 为 true", () => {
    const onExpire = jest.fn();
    const { result } = renderHook(() => useInterviewTimer(120, onExpire));

    tick(61000);
    expect(result.current.secondsLeft).toBeLessThanOrEqual(60);
    expect(result.current.isWarning).toBe(true);
  });

  it("到时只触发一次 onExpire", () => {
    const onExpire = jest.fn();
    renderHook(() => useInterviewTimer(1, onExpire));

    tick(5000);
    expect(onExpire).toHaveBeenCalledTimes(1);
  });
});
