"use client";

import { LiveKitRoom } from "@livekit/components-react";
import { useParams } from "next/navigation";
import { useState, useEffect, useMemo } from "react";
import { useTranslation } from "react-i18next";

import { AgentCall } from "@/components/AgentCall";
import { FANCALL_NS } from "@/i18n";
import { LiveRoomRepository } from "@/repositories";
import { getApiService } from "@/services/ApiService";

export default function FancallRoomPage() {
  const params = useParams();
  const { t } = useTranslation(FANCALL_NS);
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
        const response = await repository.generateToken(liveRoomId);
        setToken(response.token);
        setRoomName(response.roomName);
      } finally {
        setIsLoading(false);
      }
    })();
  }, [liveRoomId, repository]);

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center bg-black">
        <span className="loading loading-spinner loading-lg text-white" />
      </div>
    );
  }

  if (!token || !roomName) {
    return (
      <div className="flex h-full items-center justify-center bg-black">
        <div className="alert alert-error max-w-md">
          <span>{t("room.failedToLoad")}</span>
        </div>
      </div>
    );
  }

  const wsUrl = process.env.NEXT_PUBLIC_LIVEKIT_WS_URL || "";

  return (
    <div className="h-full bg-black">
      <LiveKitRoom
        token={token}
        serverUrl={wsUrl}
        connect={true}
        audio={false}
        video={false}
      >
        <AgentCall displayName={t("room.agentName")} />
      </LiveKitRoom>
    </div>
  );
}
