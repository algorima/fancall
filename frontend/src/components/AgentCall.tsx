"use client";

import {
  ChevronLeftIcon,
  PaperAirplaneIcon,
  PhoneXMarkIcon,
  SpeakerWaveIcon,
} from "@heroicons/react/24/solid";
import {
  RoomAudioRenderer,
  useVoiceAssistant,
  BarVisualizer,
  VideoTrack,
  useTracks,
  useChat,
  useRoomContext,
} from "@livekit/components-react";
import clsx from "clsx";
import { Track, RoomEvent } from "livekit-client";
import Image from "next/image";
import { useState, useCallback, useEffect } from "react";
import { useTranslation } from "react-i18next";

import { LoadingQuips } from "@/components/LoadingQuips";
import { FANCALL_NS } from "@/i18n";

export interface AgentCallProps {
  profilePictureUrl?: string | null;
  displayName: string;
  biography?: string | null;
  /** Called when the user taps the red hang-up button */
  onHangUp?: () => void;
  /** Called when the user taps the back button in the top-left corner */
  onBack?: () => void;
  /** Call length; the countdown starts when the agent joins (matches the backend timer) */
  callDurationSeconds?: number;
}

const LAST_SECONDS_WARNING = 30;

const formatRemaining = (seconds: number) => {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
};

/** Seconds left in the call, counted from the moment the agent joined */
const useRemainingSeconds = (isRunning: boolean, totalSeconds: number) => {
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (isRunning && startedAt === null) setStartedAt(Date.now());
  }, [isRunning, startedAt]);

  useEffect(() => {
    if (startedAt === null) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [startedAt]);

  if (startedAt === null) return null;
  return Math.max(0, totalSeconds - Math.floor((now - startedAt) / 1000));
};

/**
 * Agent 통화 컴포넌트
 * Agent의 비디오/오디오 스트림을 렌더링합니다.
 */
export function AgentCall({
  profilePictureUrl,
  displayName,
  biography,
  onHangUp,
  onBack,
  callDurationSeconds = 180,
}: AgentCallProps) {
  const { state, audioTrack, agent } = useVoiceAssistant();
  const { t } = useTranslation();
  const tracks = useTracks();
  const room = useRoomContext();
  const [message, setMessage] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [canPlayAudio, setCanPlayAudio] = useState(false);

  // Find agent video track
  const agentVideoTrack = tracks.find(
    (trackRef) =>
      trackRef.publication.kind === Track.Kind.Video &&
      trackRef.participant.isAgent,
  );

  // Send text message to agent via chat
  const { send } = useChat();

  // Handle audio playback status
  useEffect(() => {
    if (!room) return;

    const handleAudioPlaybackStatusChanged = () => {
      setCanPlayAudio(room.canPlaybackAudio);
    };

    // Set initial state
    setCanPlayAudio(room.canPlaybackAudio);

    // Listen for changes
    room.on(
      RoomEvent.AudioPlaybackStatusChanged,
      handleAudioPlaybackStatusChanged,
    );

    return () => {
      room.off(
        RoomEvent.AudioPlaybackStatusChanged,
        handleAudioPlaybackStatusChanged,
      );
    };
  }, [room]);

  const handleStartAudio = useCallback(async () => {
    if (!room) return;
    await room.startAudio();
  }, [room]);

  const handleSendMessage = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!message.trim() || isSending || !agent) return;

      setIsSending(true);
      try {
        await send(message.trim());
        setMessage("");
      } finally {
        setIsSending(false);
      }
    },
    [message, isSending, agent, send],
  );

  const isConnected = state !== "disconnected" && state !== "connecting";
  // Media not flowing yet: the agent and its avatar are still joining
  const isWaitingForMedia = !agentVideoTrack && !audioTrack;
  const isAgentAvailable = !!agent;
  const remainingSeconds = useRemainingSeconds(
    isAgentAvailable,
    callDurationSeconds,
  );

  return (
    <div className="relative size-full overflow-hidden bg-base-300">
      {/* Audio renderer */}
      <RoomAudioRenderer />

      {/* Full-screen like a real video call. Until video arrives, the same
          photo the avatar is animated from, so the face simply starts moving */}
      {profilePictureUrl && (
        <Image
          src={profilePictureUrl}
          alt=""
          fill
          className="object-cover"
          priority
        />
      )}
      {agentVideoTrack && (
        <VideoTrack
          trackRef={agentVideoTrack}
          className="absolute inset-0 size-full animate-fade-in object-cover"
        />
      )}

      {/* Top bar: back, name and state, time left */}
      <div className="absolute inset-x-0 top-0 z-10 bg-gradient-to-b from-base-100/80 to-transparent px-4 pb-12 pt-4 text-base-content sm:pt-14">
        <div className="grid grid-cols-[2.5rem_1fr_auto] items-start gap-2">
          {onBack ? (
            <button
              type="button"
              onClick={onBack}
              aria-label={t("agentCall.back", { ns: FANCALL_NS })}
              className="btn btn-circle btn-ghost btn-sm size-10 bg-base-content/15 backdrop-blur hover:bg-base-content/25"
            >
              <ChevronLeftIcon className="size-5" />
            </button>
          ) : (
            <span />
          )}
          <div className="flex min-w-0 flex-col items-center pt-1 text-center">
            <h1 className="truncate text-title-l">{displayName}</h1>
            {biography && !agentVideoTrack && (
              <p className="mt-1 max-w-xs text-body-s text-base-content/70">
                {biography}
              </p>
            )}
            {isWaitingForMedia ? (
              <div className="mt-1">
                <LoadingQuips />
              </div>
            ) : (
              <div
                className={clsx(
                  "mt-0.5 text-body-s font-medium transition-colors",
                  state === "speaking" && "text-secondary",
                  state === "listening" && "text-primary",
                  state === "thinking" && "text-accent",
                  (state === "connecting" || state === "disconnected") &&
                    "text-base-content/70",
                )}
              >
                {state === "connecting" &&
                  t("agentCall.state.connecting", { ns: FANCALL_NS })}
                {state === "listening" &&
                  t("agentCall.state.listening", { ns: FANCALL_NS })}
                {state === "thinking" &&
                  t("agentCall.state.thinking", { ns: FANCALL_NS })}
                {state === "speaking" &&
                  t("agentCall.state.speaking", { ns: FANCALL_NS })}
                {state === "disconnected" &&
                  t("agentCall.state.disconnected", { ns: FANCALL_NS })}
              </div>
            )}
          </div>
          <div
            className={clsx(
              "mt-1.5 min-w-[4.5rem] rounded-full px-3 py-1 text-center text-label-m tabular-nums backdrop-blur transition-colors",
              remainingSeconds !== null &&
                remainingSeconds <= LAST_SECONDS_WARNING
                ? "bg-error text-error-content"
                : "bg-base-content/15",
              remainingSeconds === null && "invisible",
            )}
            aria-live="off"
          >
            {t("agentCall.remaining", {
              ns: FANCALL_NS,
              time: formatRemaining(remainingSeconds ?? callDurationSeconds),
            })}
          </div>
        </div>
      </div>

      {/* Voice bars when the call is voice-only */}
      {audioTrack && !agentVideoTrack && (
        <div className="absolute inset-x-0 bottom-48 z-10 flex h-24 items-center justify-center">
          <BarVisualizer
            state={state}
            barCount={5}
            trackRef={audioTrack}
            className="[--lk-fg:hsl(var(--p))] [--lk-va-bar-gap:12px] [--lk-va-bar-width:16px]"
          />
        </div>
      )}

      {/* Bottom bar: chat input and hang up */}
      <div className="absolute inset-x-0 bottom-0 z-10 flex flex-col items-center gap-5 bg-gradient-to-t from-base-100/90 to-transparent px-4 pb-8 pt-16">
        <form
          onSubmit={handleSendMessage}
          className="flex w-full items-center gap-2"
        >
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            disabled={!isConnected || !isAgentAvailable || isSending}
            placeholder={
              !isConnected
                ? t("agentCall.chat.connecting", { ns: FANCALL_NS })
                : !isAgentAvailable
                  ? t("agentCall.chat.waitingForAgent", { ns: FANCALL_NS })
                  : t("agentCall.chat.placeholder", { ns: FANCALL_NS })
            }
            className="input input-sm min-w-0 flex-1 rounded-full border-none bg-base-content/15 text-body-m backdrop-blur placeholder:text-base-content/60 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={
              !message.trim() || isSending || !isConnected || !isAgentAvailable
            }
            aria-label={
              isSending
                ? t("agentCall.chat.sending", { ns: FANCALL_NS })
                : t("agentCall.chat.send", { ns: FANCALL_NS })
            }
            className="btn btn-circle btn-primary btn-sm"
          >
            <PaperAirplaneIcon className="size-4" />
          </button>
        </form>
        {onHangUp && (
          <button
            type="button"
            onClick={onHangUp}
            aria-label={t("agentCall.hangUp", { ns: FANCALL_NS })}
            className="btn btn-circle btn-error size-16 shadow-xl"
          >
            <PhoneXMarkIcon className="size-7 text-error-content" />
          </button>
        )}
      </div>

      {/* Audio permission button */}
      {!canPlayAudio && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-base-100/40 px-8 backdrop-blur-md">
          <div className="w-full max-w-xs animate-fade-up rounded-xl bg-base-200/90 px-6 pb-6 pt-8 text-center shadow-2xl ring-1 ring-base-content/10">
            <div className="mx-auto mb-5 flex size-14 items-center justify-center rounded-full bg-primary/15">
              <SpeakerWaveIcon className="size-7 text-primary" />
            </div>
            <h3 className="text-title-l text-base-content">
              {t("agentCall.audioPermission.title", { ns: FANCALL_NS })}
            </h3>
            <p className="mt-2 break-keep text-body-m text-base-content/70">
              {t("agentCall.audioPermission.description", { ns: FANCALL_NS })}
            </p>
            <button
              type="button"
              onClick={handleStartAudio}
              className="btn btn-primary btn-block mt-7 rounded-lg border-none text-label-l focus-visible:outline-offset-4"
            >
              <SpeakerWaveIcon className="size-5" />
              {t("agentCall.audioPermission.button", { ns: FANCALL_NS })}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
