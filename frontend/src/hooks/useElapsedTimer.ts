"use client";

import { useState, useEffect } from "react";
import { UrgencyLevel } from "@/types/kds";

export function useElapsedTimer(
  placedAt: string,
  targetPrepMinutes: number = 15
) {
  const calculateElapsed = () => {
    const placedTime = new Date(placedAt).getTime();
    const now = Date.now();
    const seconds = Math.max(0, Math.floor((now - placedTime) / 1000));
    return seconds;
  };

  const [elapsedSeconds, setElapsedSeconds] = useState(calculateElapsed);

  useEffect(() => {
    // 1-second dynamic tick
    const interval = setInterval(() => {
      setElapsedSeconds(calculateElapsed());
    }, 1000);

    return () => clearInterval(interval);
  }, [placedAt]);

  const minutes = Math.floor(elapsedSeconds / 60);
  const remainingSeconds = elapsedSeconds % 60;
  const formattedTime = `${String(minutes).padStart(2, "0")}:${String(
    remainingSeconds
  ).padStart(2, "0")}`;

  const targetSeconds = targetPrepMinutes * 60;
  let urgency: UrgencyLevel = "NORMAL";

  if (elapsedSeconds > targetSeconds || elapsedSeconds >= 900) {
    urgency = "DELAYED";
  } else if (elapsedSeconds >= 600) {
    urgency = "WARNING";
  }

  return {
    elapsedSeconds,
    formattedTime,
    urgency,
  };
}
