"use client";

import { useEffect, useRef, useState } from "react";

export function useInterviewTimer(initialSeconds: number, onExpire: () => void) {
  const [secondsLeft, setSecondsLeft] = useState(initialSeconds);
  const startEpochRef = useRef(0);
  const hasFiredRef = useRef(false);
  const onExpireRef = useRef(onExpire);

  onExpireRef.current = onExpire;

  useEffect(() => {
    startEpochRef.current = performance.now();
    hasFiredRef.current = false;

    if (initialSeconds <= 0) {
      setSecondsLeft(0);
      if (!hasFiredRef.current) {
        hasFiredRef.current = true;
        onExpireRef.current();
      }
      return;
    }

    const recalculate = () => {
      const elapsed = (performance.now() - startEpochRef.current) / 1000;
      const remaining = Math.max(0, initialSeconds - elapsed);
      setSecondsLeft(Math.ceil(remaining));

      if (remaining <= 0 && !hasFiredRef.current) {
        hasFiredRef.current = true;
        onExpireRef.current();
      }
    };

    recalculate();
    const timer = window.setInterval(recalculate, 100);

    const handleVisibility = () => {
      if (document.visibilityState === "visible") {
        recalculate();
      }
    };
    document.addEventListener("visibilitychange", handleVisibility);

    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [initialSeconds]);

  return {
    secondsLeft,
    isWarning: secondsLeft <= 60 && secondsLeft > 0,
  };
}
