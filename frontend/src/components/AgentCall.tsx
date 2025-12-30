"use client";

import { PaperAirplaneIcon, SpeakerWaveIcon } from "@heroicons/react/24/solid";
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

import { FANCALL_NS } from "@/i18n";

interface AgentCallProps {
  profilePictureUrl?: string | null;
  displayName: string;
  biography?: string | null;
}

/**
 * Agent 통화 컴포넌트
 * Agent의 비디오/오디오 스트림을 렌더링합니다.
 */
export function AgentCall({
  profilePictureUrl,
  displayName,
  biography,
}: AgentCallProps) {
  const { state, audioTrack, agent } = useVoiceAssistant();
  const { t } = useTranslation(FANCALL_NS);
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
  const isAgentAvailable = !!agent;

  return (
    <div className="relative flex h-full flex-col bg-base-200">
      {/* Audio renderer */}
      <RoomAudioRenderer />

      {/* Audio permission button */}
      {!canPlayAudio && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-neutral/75 backdrop-blur-sm">
          <div className="mx-4 max-w-md rounded-2xl bg-base-100 p-6 text-center shadow-2xl">
            <SpeakerWaveIcon className="mx-auto mb-4 size-12 text-warning" />
            <h3 className="mb-2 text-lg font-semibold text-base-content">
              {t("agentCall.audioPermission.title")}
            </h3>
            <p className="mb-4 text-sm text-neutral-content">
              {t("agentCall.audioPermission.description")}
            </p>
            <button
              onClick={handleStartAudio}
              className="btn btn-primary btn-block"
            >
              <SpeakerWaveIcon className="size-5" />
              {t("agentCall.audioPermission.button")}
            </button>
          </div>
        </div>
      )}

      {/* Main content area */}
      <div className="flex flex-1 flex-col items-center justify-center p-6">
        {/* Video or Profile Picture */}
        {agentVideoTrack ? (
          <div className="relative mb-6 max-h-[70vh] w-full max-w-2xl overflow-hidden rounded-2xl shadow-2xl">
            <VideoTrack
              trackRef={agentVideoTrack}
              className="size-full object-contain"
            />
          </div>
        ) : (
          <div className="mb-6 flex flex-col items-center">
            {profilePictureUrl && (
              <div className="relative mb-4 size-48 overflow-hidden rounded-full shadow-2xl ring-4 ring-primary/20">
                <Image
                  src={profilePictureUrl}
                  alt={displayName}
                  fill
                  className="object-cover"
                  priority
                />
              </div>
            )}
            <h1 className="text-3xl font-bold text-base-content">
              {displayName}
            </h1>
            {biography && (
              <p className="mt-2 max-w-md text-center text-sm text-neutral-content">
                {biography}
              </p>
            )}
          </div>
        )}

        {/* Audio visualizer */}
        {audioTrack && !agentVideoTrack && (
          <div className="mb-6 flex h-32 items-center justify-center">
            <BarVisualizer
              state={state}
              barCount={5}
              trackRef={audioTrack}
              className="[--lk-fg:hsl(var(--p))] [--lk-va-bar-gap:16px] [--lk-va-bar-width:24px]"
            />
          </div>
        )}

        {/* Agent state indicator */}
        <div
          className={clsx(
            "mb-6 text-lg font-medium transition-colors",
            state === "speaking" && "text-secondary",
            state === "listening" && "text-primary",
            state === "thinking" && "text-accent",
            (state === "connecting" || state === "disconnected") &&
              "text-neutral-content",
          )}
        >
          {state === "connecting" && t("agentCall.state.connecting")}
          {state === "listening" && t("agentCall.state.listening")}
          {state === "thinking" && t("agentCall.state.thinking")}
          {state === "speaking" && t("agentCall.state.speaking")}
          {state === "disconnected" && t("agentCall.state.disconnected")}
        </div>
      </div>

      {/* Chat input at bottom */}
      <div className="border-t border-base-300 bg-base-100 p-4">
        <form
          onSubmit={handleSendMessage}
          className="container mx-auto flex max-w-4xl items-center gap-3"
        >
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            disabled={!isConnected || !isAgentAvailable || isSending}
            placeholder={
              !isConnected
                ? t("agentCall.chat.connecting")
                : !isAgentAvailable
                  ? t("agentCall.chat.waitingForAgent")
                  : t("agentCall.chat.placeholder")
            }
            className="input input-bordered flex-1 focus:input-primary disabled:cursor-not-allowed disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={
              !message.trim() || isSending || !isConnected || !isAgentAvailable
            }
            className="btn btn-primary"
          >
            <PaperAirplaneIcon className="size-5" />
            {isSending ? t("agentCall.chat.sending") : t("agentCall.chat.send")}
          </button>
        </form>
      </div>
    </div>
  );
}
