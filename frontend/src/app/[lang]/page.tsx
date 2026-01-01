"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { StartCallSection } from "@/components/StartCallSection";
import { LiveRoomRepository } from "@/repositories";
import { getApiService } from "@/services/ApiService";

export default function FancallEntryPage() {
  const { i18n } = useTranslation();
  const router = useRouter();

  const repository = useMemo<LiveRoomRepository>(
    () => new LiveRoomRepository(getApiService()),
    [],
  );

  const [isLoading, setIsLoading] = useState(false);

  const handleStart = async () => {
    if (isLoading) return;

    setIsLoading(true);
    try {
      const response = await repository.create({ variables: {} });
      const liveRoom = response.data;
      await repository.dispatchAgent(liveRoom.id, {});

      router.push(`/${i18n.language}/${liveRoom.id}`);
      // 리디렉션 후에는 로딩 상태를 유지 (버튼 비활성화 유지)
    } catch (error) {
      console.error("Failed to start fancall:", error);
      // 오류 발생 시에만 로딩 상태 해제
      setIsLoading(false);
      // 오류를 다시 throw하여 Sentry에 자동 보고되도록 함
      throw error;
    }
  };

  return (
    <main className="flex min-h-dvh w-full flex-col items-center justify-center bg-base-100 p-6">
      <StartCallSection onStart={handleStart} isLoading={isLoading} />
    </main>
  );
}
