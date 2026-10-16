"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import {
  IncomingCallScreen,
  type IncomingCallStatus,
} from "@/components/IncomingCallScreen";
import { PhoneFrame } from "@/components/PhoneFrame";
import { FANCALL_NS } from "@/i18n";
import { LiveRoomRepository } from "@/repositories";
import { getApiService } from "@/services/ApiService";

// The avatar provider drops an avatar that stays silent for 30 seconds, so an
// unanswered call must stop ringing before then.
const RING_TIMEOUT_MS = 25_000;

export default function FancallEntryPage() {
  const { i18n, t } = useTranslation();
  const router = useRouter();

  const repository = useMemo<LiveRoomRepository>(
    () => new LiveRoomRepository(getApiService()),
    [],
  );

  // Hanging up returns here with ?ended=1; show the call as over instead of
  // ringing again, which would create a room and dispatch an agent unasked.
  const wasHungUp = useSearchParams().get("ended") === "1";
  const [status, setStatus] = useState<IncomingCallStatus>(
    wasHungUp ? "ended" : "ringing",
  );
  // Room prepared while ringing: the agent and avatar join before the fan answers
  const pendingRoom = useRef<Promise<string> | null>(null);

  const prepareRoom = useCallback(() => {
    const room = (async () => {
      const response = await repository.create({ variables: {} });
      const liveRoomId = response.data.id;
      await repository.dispatchAgent(liveRoomId, {});
      router.prefetch(`/${i18n.language}/${liveRoomId}`);
      return liveRoomId;
    })();
    // Surface failures on accept, not as an unhandled rejection while ringing
    room.catch(() => undefined);
    pendingRoom.current = room;
    return room;
  }, [repository, router, i18n.language]);

  // Start preparing as soon as the phone rings
  useEffect(() => {
    if (status !== "ringing") return;
    if (!pendingRoom.current) void prepareRoom();
    const timer = setTimeout(() => {
      pendingRoom.current = null;
      setStatus("missed");
    }, RING_TIMEOUT_MS);
    return () => clearTimeout(timer);
  }, [status, prepareRoom]);

  const connect = async (room: Promise<string>) => {
    setStatus("connecting");
    try {
      const liveRoomId = await room;
      router.push(`/${i18n.language}/${liveRoomId}`);
      // 리디렉션 후에는 연결 중 상태를 유지
    } catch (error) {
      console.error("Failed to start fancall:", error);
      pendingRoom.current = null;
      setStatus("missed");
      // 오류를 다시 throw하여 Sentry에 자동 보고되도록 함
      throw error;
    }
  };

  const handleAccept = () => {
    if (status !== "ringing") return;
    void connect(pendingRoom.current ?? prepareRoom());
  };

  const handleDecline = () => {
    pendingRoom.current = null;
    setStatus("missed");
  };

  const handleCallBack = () => {
    void connect(prepareRoom());
  };

  return (
    <PhoneFrame>
      <IncomingCallScreen
        displayName={
          process.env.NEXT_PUBLIC_FANCALL_DISPLAY_NAME ||
          t("room.agentName", { ns: FANCALL_NS })
        }
        avatarUrl={process.env.NEXT_PUBLIC_FANCALL_AVATAR_URL}
        status={status}
        onAccept={handleAccept}
        onDecline={handleDecline}
        onCallBack={handleCallBack}
      />
    </PhoneFrame>
  );
}
