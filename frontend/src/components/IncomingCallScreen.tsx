"use client";

import {
  PhoneArrowUpRightIcon,
  PhoneXMarkIcon,
  VideoCameraIcon,
} from "@heroicons/react/24/solid";
import clsx from "clsx";
import Image from "next/image";
import { useTranslation } from "react-i18next";

import { LoadingQuips } from "@/components/LoadingQuips";
import { FANCALL_NS } from "@/i18n";

export type IncomingCallStatus = "ringing" | "connecting" | "missed";

export interface IncomingCallScreenProps {
  displayName: string;
  avatarUrl?: string | null;
  status: IncomingCallStatus;
  onAccept?: () => void;
  onDecline?: () => void;
  onCallBack?: () => void;
}

const noop = () => undefined;

interface CallButtonProps {
  label: string;
  onClick: () => void;
  tone: "accept" | "decline";
  ripple?: boolean;
  children: React.ReactNode;
}

function CallButton({
  label,
  onClick,
  tone,
  ripple,
  children,
}: CallButtonProps) {
  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative size-[4.5rem]">
        {ripple && (
          <>
            <span className="absolute inset-0 animate-ripple rounded-full bg-success/40" />
            <span className="absolute inset-0 animate-ripple rounded-full bg-success/40 [animation-delay:1s]" />
          </>
        )}
        <button
          onClick={onClick}
          aria-label={label}
          className={clsx(
            "btn btn-circle relative size-[4.5rem] border-none shadow-lg transition-transform active:scale-90",
            tone === "accept" ? "btn-success" : "btn-error",
          )}
        >
          {children}
        </button>
      </div>
      <span className="text-label-l drop-shadow">{label}</span>
    </div>
  );
}

/**
 * 아이돌에게서 영상통화가 걸려 오는 수신 화면 (iPhone 연락처 포스터 형태).
 * 받기 버튼은 브라우저 오디오 재생 권한을 얻는 사용자 동작도 겸합니다.
 */
export function IncomingCallScreen({
  displayName,
  avatarUrl,
  status,
  onAccept = noop,
  onDecline = noop,
  onCallBack = noop,
}: IncomingCallScreenProps) {
  const { t } = useTranslation();

  return (
    <div className="relative flex size-full flex-col justify-between overflow-hidden text-base-content">
      {/* Caller photo fills the screen, drifting slowly while it rings */}
      {avatarUrl && (
        <Image
          src={avatarUrl}
          alt=""
          fill
          priority
          className={clsx(
            "object-cover transition-[filter,opacity] duration-700",
            status === "ringing" && "animate-slow-zoom",
            status === "missed" && "opacity-40 blur-md grayscale",
          )}
        />
      )}
      <div className="absolute inset-0 bg-gradient-to-b from-base-100/60 via-transparent via-30% to-base-100/80" />
      <div className="absolute inset-x-0 bottom-0 h-1/3 bg-gradient-to-t from-base-100/60 to-transparent backdrop-blur-[2px] [mask-image:linear-gradient(to_top,black,transparent)]" />

      {/* Caller */}
      <div className="relative z-10 flex animate-fade-up flex-col items-center px-6 pt-16 text-center sm:pt-20">
        <p className="flex items-center gap-1.5 rounded-full bg-base-100/30 px-3 py-1 text-label-l text-base-content/90 backdrop-blur-xl">
          <VideoCameraIcon className="size-3.5" />
          {status === "missed"
            ? t("entry.missed", { ns: FANCALL_NS })
            : t("entry.incoming", { ns: FANCALL_NS })}
        </p>
        <h1 className="mt-3 text-display-m tracking-tight drop-shadow-lg">
          {displayName}
        </h1>
      </div>

      {/* Actions */}
      <div className="relative z-10 flex min-h-40 animate-fade-up items-end justify-center px-12 pb-16 [animation-delay:150ms]">
        {status === "ringing" && (
          <div className="flex w-full items-start justify-between">
            <CallButton
              label={t("entry.decline", { ns: FANCALL_NS })}
              onClick={onDecline}
              tone="decline"
            >
              <PhoneXMarkIcon className="size-8 text-error-content" />
            </CallButton>
            <CallButton
              label={t("entry.accept", { ns: FANCALL_NS })}
              onClick={onAccept}
              tone="accept"
              ripple
            >
              <VideoCameraIcon className="size-8 text-success-content" />
            </CallButton>
          </div>
        )}
        {status === "connecting" && (
          <div className="flex flex-col items-center gap-3">
            <p className="text-title-s">
              {t("entry.connecting", { ns: FANCALL_NS })}
            </p>
            <LoadingQuips />
          </div>
        )}
        {status === "missed" && (
          <CallButton
            label={t("entry.callBack", { ns: FANCALL_NS })}
            onClick={onCallBack}
            tone="accept"
          >
            <PhoneArrowUpRightIcon className="size-8 text-success-content" />
          </CallButton>
        )}
      </div>
    </div>
  );
}
