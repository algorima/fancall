"use client";

import { LiveKitRoom } from "@livekit/components-react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useState, useEffect, useMemo } from "react";
import { useTranslation } from "react-i18next";

import { AgentCall } from "@/components/AgentCall";
import { IncomingCallScreen } from "@/components/IncomingCallScreen";
import { PhoneFrame } from "@/components/PhoneFrame";
import { FANCALL_NS } from "@/i18n";
import { LiveRoomRepository } from "@/repositories";
import type { TokenResponse } from "@/schemas";
import { getApiService } from "@/services/ApiService";

import { useContacts } from "../useContacts";

export default function FancallRoomPage() {
  const params = useParams();
  const router = useRouter();
  const { i18n, t } = useTranslation();
  const contactId = useSearchParams().get("contact");
  const contacts = useContacts(t("room.agentName", { ns: FANCALL_NS }));
  const contact = contacts?.find((c) => c.id === contactId) ?? contacts?.[0];
  const liveRoomId = Array.isArray(params.liveRoomId)
    ? params.liveRoomId[0]
    : params.liveRoomId;

  const repository = useMemo<LiveRoomRepository>(
    () => new LiveRoomRepository(getApiService()),
    [],
  );

  const [token, setToken] = useState<string | null>(null);
  const [roomName, setRoomName] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!liveRoomId) {
      setIsLoading(false);
      return;
    }

    void (async () => {
      try {
        const response: TokenResponse =
          await repository.generateToken(liveRoomId);
        setToken(response.token);
        setRoomName(response.roomName);
      } finally {
        setIsLoading(false);
      }
    })();
  }, [liveRoomId, repository]);

  const displayName =
    contact?.name ??
    (process.env.NEXT_PUBLIC_FANCALL_DISPLAY_NAME ||
      t("room.agentName", { ns: FANCALL_NS }));
  const avatarUrl =
    contact?.photoUrl ?? process.env.NEXT_PUBLIC_FANCALL_AVATAR_URL;
  const callPhotoUrl = contact?.callPhotoUrl ?? avatarUrl;
  // Must match the worker's FANCALL_CALL_DURATION_SECONDS
  const callDurationSeconds =
    Number(process.env.NEXT_PUBLIC_FANCALL_CALL_DURATION_SECONDS) || undefined;

  if (isLoading) {
    return (
      <PhoneFrame>
        <IncomingCallScreen
          displayName={displayName}
          avatarUrl={avatarUrl}
          status="connecting"
        />
      </PhoneFrame>
    );
  }

  if (!token || !roomName) {
    return (
      <PhoneFrame>
        <div className="flex size-full items-center justify-center p-6">
          <div className="alert alert-error">
            <span>{t("room.failedToLoad", { ns: FANCALL_NS })}</span>
          </div>
        </div>
      </PhoneFrame>
    );
  }

  const wsUrl = process.env.NEXT_PUBLIC_LIVEKIT_WS_URL || "";
  const leaveCall = () => router.push(`/${i18n.language}`);

  return (
    <PhoneFrame>
      <LiveKitRoom
        token={token}
        serverUrl={wsUrl}
        connect={true}
        audio={false}
        video={false}
        className="size-full"
      >
        <AgentCall
          displayName={displayName}
          profilePictureUrl={callPhotoUrl}
          callDurationSeconds={callDurationSeconds}
          videoRegion={contact?.videoRegion}
          onHangUp={leaveCall}
          onBack={leaveCall}
        />
      </LiveKitRoom>
    </PhoneFrame>
  );
}
