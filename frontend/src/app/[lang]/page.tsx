"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { StartCallSection } from "@/components/StartCallSection";
import { FANCALL_NS } from "@/i18n";
import { LiveRoomRepository } from "@/repositories";
import { getApiService } from "@/services/ApiService";

export default function FancallEntryPage() {
  const { i18n } = useTranslation(FANCALL_NS);
  const router = useRouter();

  const repository = useMemo<LiveRoomRepository>(
    () => new LiveRoomRepository(getApiService()),
    [],
  );

  const [isLoading, setIsLoading] = useState(false);

  const handleStart = async () => {
    if (isLoading) return;

    setIsLoading(true);

    const { data: liveRoom } = await repository.create({ variables: {} });
    await repository.dispatchAgent(liveRoom.id, {});

    router.push(`/${i18n.language}/${liveRoom.id}`);
  };

  return (
    <main className="flex min-h-dvh w-full flex-col items-center justify-center bg-base-100 p-6">
      <StartCallSection onStart={handleStart} isLoading={isLoading} />
    </main>
  );
}
