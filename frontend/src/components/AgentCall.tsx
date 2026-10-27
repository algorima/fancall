"use client";

import {
  ChevronLeftIcon,
  ClockIcon,
  HeartIcon,
  PaperAirplaneIcon,
  PhoneXMarkIcon,
  SpeakerWaveIcon,
  SpeakerXMarkIcon,
  UserIcon,
  VideoCameraSlashIcon,
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
import { useState, useCallback, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";

import type { ClipMode } from "@/components/clipGraph";
import { ClipGraphPlayer } from "@/components/ClipGraphPlayer";
import { LoadingQuips } from "@/components/LoadingQuips";
import { parseTranscriptLine, TRANSCRIPT_TOPIC } from "@/components/transcript";
import {
  coverRegionRect,
  photoAspectFromRegion,
  type Size,
} from "@/components/videoLayout";
import { FANCALL_NS } from "@/i18n";
import type { ClipGraph, MemoryLine, VideoRegion } from "@/schemas";

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
  /** Where the avatar video sits in the profile picture (see VideoRegion) */
  videoRegion?: VideoRegion | null;
  /** Pre-rendered reaction clips; when set, they replace the avatar video */
  clipGraph?: ClipGraph | null;
  /** Messages the fan may send in this call. Unlimited when omitted */
  messageLimit?: number;
  /**
   * Called once the idol has answered the last allowed message
   * (or MESSAGE_LIMIT_FALLBACK_MS after it was sent, if no answer comes)
   */
  onMessageLimitReached?: () => void;
  /** Called for each line spoken in the call, so the host app can store it as memory */
  onTranscriptLine?: (line: MemoryLine) => void;
}

const LAST_SECONDS_WARNING = 30;
// Wave goodbye in the final seconds of the call
const CLOSING_SECONDS = 6;
const MAX_VISIBLE_MESSAGES = 3;
// Narrower than 3:4 counts as portrait video that can fill the phone screen
const PORTRAIT_ASPECT = 0.75;
// Show only the face and hair of the video, fading into the photo underneath.
// Lip-sync avatars move only the face, and on a wider (upper-body) call photo
// the square video's shoulders would not line up with the photo's.
const FEATHER_MASK =
  "radial-gradient(ellipse 36% 44% at 50% 47%, black 70%, transparent 100%)";
const HEART_LIFETIME_MS = 1800;
// Report the message limit even if the idol never answers the last message
export const MESSAGE_LIMIT_FALLBACK_MS = 20_000;
const HEART_TONES = ["text-error", "text-secondary", "text-primary"];

interface FloatingHeart {
  id: number;
  /** Sideways drift at the top of the float, as a CSS length */
  drift: string;
}

const formatRemaining = (seconds: number) => {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
};

/** Size of an element, kept up to date as it resizes */
const useElementSize = () => {
  const ref = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState<Size | null>(null);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect;
      setSize({ width, height });
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  return { ref, size };
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
  onHangUp,
  onBack,
  callDurationSeconds = 180,
  videoRegion,
  clipGraph,
  messageLimit,
  onMessageLimitReached,
  onTranscriptLine,
}: AgentCallProps) {
  const { state, audioTrack, agent } = useVoiceAssistant();
  const { t } = useTranslation();
  const tracks = useTracks();
  const room = useRoomContext();
  const [message, setMessage] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [canPlayAudio, setCanPlayAudio] = useState(false);
  const [isSoundMuted, setIsSoundMuted] = useState(false);
  const [hearts, setHearts] = useState<FloatingHeart[]>([]);
  const nextHeartId = useRef(0);
  const [sentCount, setSentCount] = useState(0);
  const hasFinalReplyStartedRef = useRef(false);
  const hasReportedLimitRef = useRef(false);
  const hasMessageLimit = messageLimit !== undefined;
  const isMessageLimitReached = hasMessageLimit && sentCount >= messageLimit;
  const remainingMessages = hasMessageLimit
    ? Math.max(messageLimit - sentCount, 0)
    : null;
  // Width / height of the avatar video, known once its first frame arrives
  const [videoAspect, setVideoAspect] = useState<number | null>(null);
  const isPortraitVideo = videoAspect !== null && videoAspect < PORTRAIT_ASPECT;
  const { ref: screenRef, size: screenSize } = useElementSize();
  // The avatar was made from a crop of the profile picture: put the video
  // back on that crop so the whole screen looks like one moving picture
  const regionRect =
    videoRegion && profilePictureUrl && screenSize && !isPortraitVideo
      ? coverRegionRect(
          screenSize,
          photoAspectFromRegion(videoRegion, videoAspect ?? 1),
          videoRegion,
        )
      : null;

  // Find agent video track
  const agentVideoTrack = tracks.find(
    (trackRef) =>
      trackRef.publication.kind === Track.Kind.Video &&
      trackRef.participant.isAgent,
  );

  // Send text message to agent via chat
  const { send, chatMessages } = useChat();

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

  // Each spoken line comes from the agent as it happens
  useEffect(() => {
    if (!room || !onTranscriptLine) return;
    const handleData = (
      payload: Uint8Array,
      _participant?: unknown,
      _kind?: unknown,
      topic?: string,
    ) => {
      if (topic !== TRANSCRIPT_TOPIC) return;
      const line = parseTranscriptLine(payload);
      if (line) onTranscriptLine(line);
    };
    room.on(RoomEvent.DataReceived, handleData);
    return () => {
      room.off(RoomEvent.DataReceived, handleData);
    };
  }, [room, onTranscriptLine]);

  const handleStartAudio = useCallback(async () => {
    if (!room) return;
    await room.startAudio();
  }, [room]);

  const handleSendMessage = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!message.trim() || isSending || !agent || isMessageLimitReached) {
        return;
      }

      setIsSending(true);
      try {
        await send(message.trim());
        setMessage("");
        setSentCount((count) => count + 1);
      } finally {
        setIsSending(false);
      }
    },
    [message, isSending, agent, isMessageLimitReached, send],
  );

  const reportMessageLimit = useCallback(() => {
    if (hasReportedLimitRef.current) return;
    hasReportedLimitRef.current = true;
    onMessageLimitReached?.();
  }, [onMessageLimitReached]);

  // The answer to the last allowed message has finished (speaking → listening)
  useEffect(() => {
    if (!isMessageLimitReached) return;
    if (state === "speaking") {
      hasFinalReplyStartedRef.current = true;
      return;
    }
    if (hasFinalReplyStartedRef.current && state === "listening") {
      reportMessageLimit();
    }
  }, [state, isMessageLimitReached, reportMessageLimit]);

  useEffect(() => {
    if (!isMessageLimitReached) return;
    const timer = setTimeout(reportMessageLimit, MESSAGE_LIMIT_FALLBACK_MS);
    return () => clearTimeout(timer);
  }, [isMessageLimitReached, reportMessageLimit]);

  // Hearts stay on this screen, like tapping the like button on a live stream
  const sendHeart = useCallback(() => {
    const id = nextHeartId.current++;
    const drift = `${Math.round((Math.random() - 0.5) * 48)}px`;
    setHearts((current) => [...current, { id, drift }]);
    setTimeout(() => {
      setHearts((current) => current.filter((heart) => heart.id !== id));
    }, HEART_LIFETIME_MS);
  }, []);

  const isConnected = state !== "disconnected" && state !== "connecting";
  // Media not flowing yet: the agent and its avatar are still joining
  const isWaitingForMedia = !agentVideoTrack && !audioTrack;
  const isAgentAvailable = !!agent;
  const remainingSeconds = useRemainingSeconds(
    isAgentAvailable,
    callDurationSeconds,
  );

  const stateLabel = t(`agentCall.state.${state}`, {
    ns: FANCALL_NS,
    defaultValue: "",
  });
  const recentMessages = chatMessages.slice(-MAX_VISIBLE_MESSAGES);
  const clipMode: ClipMode =
    remainingSeconds !== null && remainingSeconds <= CLOSING_SECONDS
      ? "closing"
      : state === "speaking"
        ? "speaking"
        : state === "thinking"
          ? "thinking"
          : "listening";
  const isLastSeconds =
    remainingSeconds !== null && remainingSeconds <= LAST_SECONDS_WARNING;

  return (
    <div
      ref={screenRef}
      className="relative size-full overflow-hidden bg-base-300"
    >
      {/* Audio renderer */}
      <RoomAudioRenderer muted={isSoundMuted} />

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
      {clipGraph && (
        <ClipGraphPlayer
          graph={clipGraph}
          mode={clipMode}
          className="absolute inset-0 size-full"
        />
      )}
      {!clipGraph && agentVideoTrack && !isPortraitVideo && !regionRect && (
        // Square avatars (Simli) would be cropped and zoomed by object-cover on a
        // tall phone. Fill the screen with a blurred copy instead and show the
        // real frame at full width, so the face keeps its natural size.
        <VideoTrack
          trackRef={agentVideoTrack}
          aria-hidden
          className="absolute inset-0 size-full scale-125 animate-fade-in object-cover blur-2xl brightness-75"
        />
      )}
      {!clipGraph && agentVideoTrack && (
        <VideoTrack
          trackRef={agentVideoTrack}
          onResize={(e) => {
            const { videoWidth, videoHeight } = e.currentTarget;
            if (videoWidth && videoHeight) {
              setVideoAspect(videoWidth / videoHeight);
            }
          }}
          style={
            regionRect
              ? {
                  ...regionRect,
                  maskImage: FEATHER_MASK,
                  WebkitMaskImage: FEATHER_MASK,
                }
              : undefined
          }
          className={clsx(
            "absolute animate-fade-in",
            isPortraitVideo && "inset-0 size-full object-cover",
            regionRect && "object-fill",
            !isPortraitVideo &&
              !regionRect &&
              "inset-x-0 top-[45%] aspect-square w-full -translate-y-1/2 object-cover [mask-image:linear-gradient(to_bottom,transparent,black_10%,black_90%,transparent)]",
          )}
        />
      )}

      {/* Scrims keep the overlays readable on any video */}
      <div className="pointer-events-none absolute inset-x-0 top-0 h-40 bg-gradient-to-b from-base-100/60 to-transparent" />
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-80 bg-gradient-to-t from-base-100/80 via-base-100/30 to-transparent" />

      {/* Top bar: back, caller, time left */}
      <div className="absolute inset-x-0 top-0 z-10 flex items-center gap-3 px-4 pt-4 text-base-content sm:pt-14">
        {onBack && (
          <button
            type="button"
            onClick={onBack}
            aria-label={t("agentCall.back", { ns: FANCALL_NS })}
            className="btn btn-circle btn-ghost size-10 min-h-0 shrink-0 border-none bg-base-100/30 backdrop-blur-xl hover:bg-base-100/50"
          >
            <ChevronLeftIcon className="size-5" />
          </button>
        )}
        <div className="flex min-w-0 flex-1 items-center gap-2.5">
          {profilePictureUrl && (
            <Image
              src={profilePictureUrl}
              alt=""
              width={36}
              height={36}
              className="size-9 shrink-0 rounded-full object-cover ring-2 ring-base-content/30"
            />
          )}
          <div className="min-w-0">
            <h1 className="truncate text-title-s drop-shadow">{displayName}</h1>
            <p className="flex items-center gap-1.5 text-label-m text-base-content/80 drop-shadow">
              <span
                className={clsx(
                  "size-1.5 shrink-0 rounded-full transition-colors",
                  state === "speaking" && "bg-secondary",
                  state === "listening" && "bg-primary",
                  state === "thinking" && "bg-accent",
                  (state === "connecting" || state === "disconnected") &&
                    "bg-base-content/50",
                )}
              />
              {isWaitingForMedia ? (
                <span className="min-w-0 flex-1">
                  <LoadingQuips inline />
                </span>
              ) : (
                <span className="truncate">{stateLabel}</span>
              )}
            </p>
          </div>
        </div>
        <div
          className={clsx(
            "flex shrink-0 items-center gap-1 rounded-full px-3 py-1.5 text-label-m tabular-nums ring-1 backdrop-blur-xl transition-colors",
            isLastSeconds
              ? "animate-pulse bg-error text-error-content ring-error"
              : "bg-base-100/30 ring-base-content/10",
            remainingSeconds === null && "invisible",
          )}
          aria-live="off"
        >
          <ClockIcon className="size-3.5" />
          {t("agentCall.remaining", {
            ns: FANCALL_NS,
            time: formatRemaining(remainingSeconds ?? callDurationSeconds),
          })}
        </div>
      </div>

      {/* Self view. The fan joins without a camera, so it shows the camera-off tile */}
      <div className="absolute right-4 top-[4.5rem] z-10 flex aspect-[3/4] w-[5.5rem] flex-col items-center justify-center gap-2 overflow-hidden rounded-2xl bg-base-200/60 shadow-xl ring-1 ring-base-content/15 backdrop-blur-xl sm:top-28">
        <span className="flex size-10 items-center justify-center rounded-full bg-base-content/15">
          <UserIcon className="size-5 text-base-content/70" />
        </span>
        <span className="flex items-center gap-1 text-label-s text-base-content/70">
          <VideoCameraSlashIcon className="size-3" />
          {t("agentCall.cameraOff", { ns: FANCALL_NS })}
        </span>
      </div>

      {/* Voice bars when the call is voice-only */}
      {audioTrack && !agentVideoTrack && (
        <div className="absolute inset-x-0 bottom-64 z-10 flex h-24 items-center justify-center">
          <BarVisualizer
            state={state}
            barCount={5}
            trackRef={audioTrack}
            className="[--lk-fg:hsl(var(--p))] [--lk-va-bar-gap:12px] [--lk-va-bar-width:16px]"
          />
        </div>
      )}

      {/* Bottom: recent messages, message input with hearts, call controls */}
      <div className="absolute inset-x-0 bottom-0 z-10 flex flex-col gap-3 px-4 pb-6 text-base-content sm:pb-8">
        {recentMessages.length > 0 && (
          <ul className="flex flex-col items-start gap-1.5 pr-14">
            {recentMessages.map((msg) => (
              <li
                key={msg.id}
                className="max-w-full animate-fade-up break-words rounded-2xl bg-base-100/35 px-3 py-1.5 text-body-s backdrop-blur-md"
              >
                <span className="mr-1.5 font-semibold text-base-content/70">
                  {msg.from?.isLocal
                    ? t("agentCall.you", { ns: FANCALL_NS })
                    : displayName}
                </span>
                {msg.message}
              </li>
            ))}
          </ul>
        )}

        <div className="flex items-center gap-2">
          <form
            onSubmit={handleSendMessage}
            className="relative min-w-0 flex-1"
          >
            <input
              type="text"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              disabled={
                !isConnected ||
                !isAgentAvailable ||
                isSending ||
                isMessageLimitReached
              }
              placeholder={
                !isConnected
                  ? t("agentCall.chat.connecting", { ns: FANCALL_NS })
                  : !isAgentAvailable
                    ? t("agentCall.chat.waitingForAgent", { ns: FANCALL_NS })
                    : isMessageLimitReached
                      ? t("agentCall.chat.limitReached", { ns: FANCALL_NS })
                      : remainingMessages !== null
                        ? t("agentCall.chat.remaining", {
                            ns: FANCALL_NS,
                            count: remainingMessages,
                          })
                        : t("agentCall.chat.placeholder", { ns: FANCALL_NS })
              }
              className="input h-11 w-full rounded-full border-none bg-base-content/15 pl-4 pr-12 text-body-m backdrop-blur-xl placeholder:text-base-content/60 focus:outline-none disabled:cursor-not-allowed disabled:bg-base-content/10 disabled:placeholder:text-base-content/40"
            />
            <button
              type="submit"
              disabled={
                !message.trim() ||
                isSending ||
                !isConnected ||
                !isAgentAvailable ||
                isMessageLimitReached
              }
              aria-label={
                isSending
                  ? t("agentCall.chat.sending", { ns: FANCALL_NS })
                  : t("agentCall.chat.send", { ns: FANCALL_NS })
              }
              className={clsx(
                "btn btn-circle btn-primary absolute right-1 top-1 size-9 min-h-0 border-none transition-[opacity,transform]",
                !message.trim() && "scale-75 opacity-0",
              )}
            >
              <PaperAirplaneIcon className="size-4" />
            </button>
          </form>

          <div className="relative shrink-0">
            {hearts.map((heart) => (
              <HeartIcon
                key={heart.id}
                aria-hidden
                style={{ "--heart-drift": heart.drift } as React.CSSProperties}
                className={clsx(
                  "pointer-events-none absolute bottom-full left-2 size-7 animate-float-heart drop-shadow",
                  HEART_TONES[heart.id % HEART_TONES.length],
                )}
              />
            ))}
            <button
              type="button"
              onClick={sendHeart}
              aria-label={t("agentCall.sendHeart", { ns: FANCALL_NS })}
              className="btn btn-circle size-11 min-h-0 border-none bg-base-content/15 backdrop-blur-xl transition-transform hover:bg-base-content/25 active:scale-90"
            >
              <HeartIcon className="size-6 text-error" />
            </button>
          </div>
        </div>

        <div className="flex items-center gap-4 self-center rounded-full bg-base-100/30 p-2 ring-1 ring-base-content/10 backdrop-blur-2xl">
          <button
            type="button"
            onClick={() => setIsSoundMuted((muted) => !muted)}
            aria-pressed={isSoundMuted}
            aria-label={
              isSoundMuted
                ? t("agentCall.speaker.unmute", { ns: FANCALL_NS })
                : t("agentCall.speaker.mute", { ns: FANCALL_NS })
            }
            className={clsx(
              "btn btn-circle size-14 min-h-0 border-none transition-colors",
              isSoundMuted
                ? "bg-base-content text-base-100 hover:bg-base-content/90"
                : "bg-base-content/15 text-base-content hover:bg-base-content/25",
            )}
          >
            {isSoundMuted ? (
              <SpeakerXMarkIcon className="size-6" />
            ) : (
              <SpeakerWaveIcon className="size-6" />
            )}
          </button>
          {onHangUp && (
            <button
              type="button"
              onClick={onHangUp}
              aria-label={t("agentCall.hangUp", { ns: FANCALL_NS })}
              className="btn btn-circle btn-error size-14 min-h-0 border-none"
            >
              <PhoneXMarkIcon className="size-6 text-error-content" />
            </button>
          )}
        </div>
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
