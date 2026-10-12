"use client";

import {
  ChatBubbleOvalLeftIcon,
  ChevronLeftIcon,
  EnvelopeIcon,
  PhoneIcon,
  VideoCameraIcon,
} from "@heroicons/react/24/solid";
import clsx from "clsx";
import Image from "next/image";
import { useTranslation } from "react-i18next";

import { FANCALL_NS } from "@/i18n";
import type { Contact } from "@/schemas";

export interface ContactCardProps {
  contact: Contact;
  onBack: () => void;
  onVideoCall: () => void;
}

interface ActionProps {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  onClick?: () => void;
}

function Action({ label, icon: Icon, onClick }: ActionProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!onClick}
      className={clsx(
        "flex flex-1 flex-col items-center gap-1 rounded-xl bg-base-content/15 py-2 backdrop-blur-xl transition-transform active:scale-95",
        !onClick && "opacity-40",
      )}
    >
      <Icon className="size-5" />
      <span className="text-label-s">{label}</span>
    </button>
  );
}

/**
 * iPhone 연락처 카드(연락처 포스터) 형태의 상세 화면.
 * 영상통화 버튼으로 통화를 겁니다. 이 데모에서는 영상통화만 동작합니다.
 */
export function ContactCard({
  contact,
  onBack,
  onVideoCall,
}: ContactCardProps) {
  const { t } = useTranslation();

  return (
    <div className="relative flex size-full animate-fade-in flex-col overflow-y-auto bg-base-100 text-base-content">
      {/* Contact poster */}
      <div className="relative h-[62%] min-h-80 w-full shrink-0">
        <Image
          src={contact.photoUrl}
          alt=""
          fill
          priority
          sizes="(min-width: 640px) 36rem, 100vw"
          className="object-cover object-top"
        />
        <div className="absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-base-100 via-base-100/50 to-transparent" />
        <button
          type="button"
          onClick={onBack}
          className="absolute left-2 top-4 z-10 flex items-center rounded-full bg-base-100/30 py-1.5 pl-1 pr-3 text-body-l backdrop-blur-xl sm:top-14"
        >
          <ChevronLeftIcon className="size-5" />
          {t("contacts.title", { ns: FANCALL_NS })}
        </button>
        <h1 className="absolute inset-x-0 bottom-4 px-6 text-center text-display-m font-bold tracking-tight drop-shadow-lg">
          {contact.name}
        </h1>
      </div>

      <div className="flex gap-2 px-4">
        <Action
          label={t("contacts.message", { ns: FANCALL_NS })}
          icon={ChatBubbleOvalLeftIcon}
        />
        <Action
          label={t("contacts.call", { ns: FANCALL_NS })}
          icon={PhoneIcon}
        />
        <Action
          label={t("contacts.video", { ns: FANCALL_NS })}
          icon={VideoCameraIcon}
          onClick={onVideoCall}
        />
        <Action
          label={t("contacts.mail", { ns: FANCALL_NS })}
          icon={EnvelopeIcon}
        />
      </div>

      <div className="mx-4 mb-10 mt-4 flex items-center justify-between rounded-xl bg-base-content/10 px-4 py-3">
        <span className="text-body-l">FaceTime</span>
        <span className="flex gap-5 text-primary">
          <button
            type="button"
            onClick={onVideoCall}
            aria-label={t("contacts.video", { ns: FANCALL_NS })}
          >
            <VideoCameraIcon className="size-6" />
          </button>
          <PhoneIcon className="size-6 opacity-40" />
        </span>
      </div>
    </div>
  );
}
