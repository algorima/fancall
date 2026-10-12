"use client";

import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { FANCALL_NS } from "@/i18n";

export interface LoadingQuipsProps {
  /** Milliseconds each quip stays on screen */
  intervalMs?: number;
}

// One shuffled order per page load, shared by every LoadingQuips instance.
// The call flow mounts this on several screens in a row, so a shared cursor
// keeps it moving through the list instead of restarting and repeating.
let order: number[] = [];
let cursor = 0;

const nextQuipIndex = (count: number) => {
  if (order.length !== count) {
    order = Array.from({ length: count }, (_, i) => i);
    for (let i = count - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [order[i], order[j]] = [order[j], order[i]];
    }
    cursor = 0;
  }
  const index = order[cursor % count];
  cursor += 1;
  return index;
};

/**
 * 연결을 기다리는 동안 재미있는 문구를 돌아가며 보여줍니다.
 */
export function LoadingQuips({ intervalMs = 2800 }: LoadingQuipsProps) {
  const { t } = useTranslation();
  const raw: unknown = t("loadingQuips", {
    ns: FANCALL_NS,
    returnObjects: true,
  });
  const quips = Array.isArray(raw)
    ? raw.filter((q): q is string => typeof q === "string")
    : [];
  // Chosen after mount so server and client render the same markup
  const [index, setIndex] = useState<number | null>(null);

  useEffect(() => {
    if (quips.length === 0) return;
    setIndex(nextQuipIndex(quips.length));
    const timer = setInterval(() => {
      setIndex(nextQuipIndex(quips.length));
    }, intervalMs);
    return () => clearInterval(timer);
  }, [quips.length, intervalMs]);

  return (
    <div
      className="flex items-center gap-2 text-body-m opacity-80"
      aria-live="polite"
    >
      <span className="loading loading-dots loading-sm" />
      {index !== null && (
        <span key={index} className="animate-fade-up">
          {quips[index]}
        </span>
      )}
    </div>
  );
}
