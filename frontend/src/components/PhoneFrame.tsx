"use client";

import { Battery100Icon, WifiIcon } from "@heroicons/react/24/solid";
import { useEffect, useState } from "react";

export interface PhoneFrameProps {
  children: React.ReactNode;
}

const formatClock = (date: Date) =>
  date.toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
    hour12: false,
  });

/**
 * 통화 화면을 세로 영상통화 비율(9:16)로 고정합니다.
 * 모바일에서는 화면 전체를 쓰고, 넓은 화면에서는 가운데에 휴대폰 모양으로 띄웁니다.
 * 실제 휴대폰에는 기기 상태 표시줄이 있으므로, 상태 표시줄은 넓은 화면에서만 그립니다.
 * 통화 화면은 항상 어두운 테마로 그립니다.
 */
export function PhoneFrame({ children }: PhoneFrameProps) {
  // Set after mount so server and client render the same markup
  const [clock, setClock] = useState<string | null>(null);

  useEffect(() => {
    const tick = () => setClock(formatClock(new Date()));
    tick();
    const timer = setInterval(tick, 15_000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="flex h-dvh w-full items-center justify-center bg-base-300">
      <div
        data-theme="dark"
        className="relative h-dvh w-full overflow-hidden bg-base-100 text-base-content sm:aspect-[9/16] sm:h-[min(calc(100dvh-3rem),64rem)] sm:w-auto sm:rounded-[3rem] sm:shadow-2xl sm:outline sm:outline-1 sm:outline-offset-[0.6rem] sm:outline-base-content/25 sm:ring-[0.6rem] sm:ring-base-100"
      >
        {children}

        {/* Status bar and island, drawn over the screen like a real phone */}
        <div className="pointer-events-none absolute inset-x-0 top-0 z-40 hidden h-12 items-center justify-between px-9 text-label-l font-semibold text-base-content sm:flex">
          <span className="w-12 text-center tabular-nums">{clock}</span>
          <span className="h-[1.9rem] w-[6.75rem] rounded-full bg-base-100" />
          <span className="flex w-12 items-center justify-end gap-1">
            <span className="flex h-3 items-end gap-px" aria-hidden>
              <span className="h-1 w-[3px] rounded-sm bg-current" />
              <span className="h-1.5 w-[3px] rounded-sm bg-current" />
              <span className="h-2 w-[3px] rounded-sm bg-current" />
              <span className="h-3 w-[3px] rounded-sm bg-current" />
            </span>
            <WifiIcon className="size-4" />
            <Battery100Icon className="size-5" />
          </span>
        </div>

        {/* Home indicator */}
        <span className="pointer-events-none absolute bottom-2 left-1/2 z-40 hidden h-[0.3rem] w-32 -translate-x-1/2 rounded-full bg-base-content/80 sm:block" />
      </div>
    </div>
  );
}
