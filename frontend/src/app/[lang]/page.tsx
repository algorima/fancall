"use client";

import { useRouter } from "next/navigation";
import { useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { ContactCard } from "@/components/ContactCard";
import { ContactsScreen } from "@/components/ContactsScreen";
import { IncomingCallScreen } from "@/components/IncomingCallScreen";
import { PhoneFrame } from "@/components/PhoneFrame";
import { FANCALL_NS } from "@/i18n";
import { LiveRoomRepository } from "@/repositories";
import type { Contact } from "@/schemas";
import { getApiService } from "@/services/ApiService";

import { useContacts } from "./useContacts";

// Let it ring a little before the idol picks up, like a real call
const MIN_RING_MS = 3_000;

const wait = (ms: number) =>
  new Promise<void>((resolve) => {
    setTimeout(resolve, ms);
  });

export default function FancallContactsPage() {
  const { i18n, t } = useTranslation();
  const router = useRouter();
  const contacts = useContacts(t("room.agentName", { ns: FANCALL_NS }));

  const repository = useMemo<LiveRoomRepository>(
    () => new LiveRoomRepository(getApiService()),
    [],
  );

  const [selected, setSelected] = useState<Contact | null>(null);
  const [isCalling, setIsCalling] = useState(false);
  // Bumped on hang-up so a call still being set up does not open the room
  const callAttempt = useRef(0);

  const startVideoCall = async (contact: Contact) => {
    const attempt = ++callAttempt.current;
    const callPhoto = contact.callPhotoUrl ?? contact.photoUrl;
    setIsCalling(true);
    try {
      const [liveRoomId] = await Promise.all([
        (async () => {
          const response = await repository.create({ variables: {} });
          const roomId = response.data.id;
          await repository.dispatchAgent(roomId, {
            avatarId: contact.avatarId,
            // Only remote images can be animated by the avatar provider
            profilePictureUrl: callPhoto.startsWith("http") ? callPhoto : null,
            voiceId: contact.voiceId,
            systemPrompt: contact.systemPrompt,
          });
          return roomId;
        })(),
        wait(MIN_RING_MS),
      ]);
      if (attempt !== callAttempt.current) return;
      router.push(
        `/${i18n.language}/${liveRoomId}?contact=${encodeURIComponent(contact.id)}`,
      );
      // 리디렉션 후에는 거는 중 화면을 유지
    } catch (error) {
      console.error("Failed to start fancall:", error);
      setIsCalling(false);
      // 오류를 다시 throw하여 Sentry에 자동 보고되도록 함
      throw error;
    }
  };

  const hangUp = () => {
    callAttempt.current++;
    setIsCalling(false);
  };

  return (
    <PhoneFrame>
      {selected && isCalling ? (
        <IncomingCallScreen
          displayName={selected.name}
          avatarUrl={selected.photoUrl}
          status="calling"
          onDecline={hangUp}
        />
      ) : selected ? (
        <ContactCard
          contact={selected}
          onBack={() => setSelected(null)}
          onVideoCall={() => void startVideoCall(selected)}
        />
      ) : (
        contacts && (
          <ContactsScreen contacts={contacts} onSelect={setSelected} />
        )
      )}
    </PhoneFrame>
  );
}
