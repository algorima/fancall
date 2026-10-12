"use client";

import { MagnifyingGlassIcon, MicrophoneIcon } from "@heroicons/react/24/solid";
import Image from "next/image";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { FANCALL_NS } from "@/i18n";
import type { Contact } from "@/schemas";

export interface ContactsScreenProps {
  contacts: Contact[];
  onSelect: (contact: Contact) => void;
}

interface Section {
  letter: string;
  contacts: Contact[];
}

const sectionLetter = (name: string) => {
  const first = name.trim().charAt(0).toUpperCase();
  return /[A-Z]/.test(first) ? first : "#";
};

/** Contacts sorted by name and grouped under their first letter, like iOS */
const groupByLetter = (contacts: Contact[]): Section[] => {
  const sorted = [...contacts].sort((a, b) => a.name.localeCompare(b.name));
  const sections: Section[] = [];
  for (const contact of sorted) {
    const letter = sectionLetter(contact.name);
    const last = sections.at(-1);
    if (last?.letter === letter) last.contacts.push(contact);
    else sections.push({ letter, contacts: [contact] });
  }
  return sections;
};

/**
 * iPhone 연락처 앱 형태의 아이돌 목록.
 * 이름을 누르면 연락처 카드로 이동합니다.
 */
export function ContactsScreen({ contacts, onSelect }: ContactsScreenProps) {
  const { t } = useTranslation();
  const [query, setQuery] = useState("");

  const sections = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    return groupByLetter(
      keyword
        ? contacts.filter((c) => c.name.toLowerCase().includes(keyword))
        : contacts,
    );
  }, [contacts, query]);

  const scrollToLetter = (letter: string) => {
    document
      .getElementById(`contacts-${letter}`)
      ?.scrollIntoView({ block: "start" });
  };

  return (
    <div className="relative flex size-full flex-col bg-base-100 text-base-content">
      <div className="shrink-0 px-4 pb-2 pt-6 sm:pt-16">
        <h1 className="text-display-s font-bold tracking-tight">
          {t("contacts.title", { ns: FANCALL_NS })}
        </h1>
        <label className="mt-3 flex h-9 items-center gap-1.5 rounded-[0.6rem] bg-base-content/10 px-2 text-base-content/50">
          <MagnifyingGlassIcon className="size-4 shrink-0" />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t("contacts.search", { ns: FANCALL_NS })}
            aria-label={t("contacts.search", { ns: FANCALL_NS })}
            className="min-w-0 flex-1 bg-transparent text-body-l text-base-content outline-none placeholder:text-base-content/50"
          />
          <MicrophoneIcon className="size-4 shrink-0" />
        </label>
      </div>

      <div className="relative min-h-0 flex-1 overflow-y-auto pb-10">
        {sections.length === 0 && (
          <p className="pt-24 text-center text-title-m text-base-content/50">
            {t("contacts.noResults", { ns: FANCALL_NS })}
          </p>
        )}
        {sections.map((section) => (
          <section key={section.letter} id={`contacts-${section.letter}`}>
            <h2 className="sticky top-0 z-10 bg-base-100 px-4 pb-1 pt-3 text-label-l font-semibold text-base-content/50">
              {section.letter}
            </h2>
            <ul>
              {section.contacts.map((contact) => (
                <li key={contact.id}>
                  <button
                    type="button"
                    onClick={() => onSelect(contact)}
                    className="flex w-full items-center gap-3 pl-4 text-left transition-colors active:bg-base-content/10"
                  >
                    <span className="relative size-10 shrink-0 overflow-hidden rounded-full bg-base-content/10">
                      <Image
                        src={contact.photoUrl}
                        alt=""
                        fill
                        sizes="40px"
                        // Center the face of a tall video-call photo
                        className="object-cover object-[50%_40%]"
                      />
                    </span>
                    <span className="flex-1 border-b border-base-content/15 py-3 pr-8 text-body-l font-semibold">
                      {contact.name}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </section>
        ))}
        <p className="py-6 text-center text-body-m text-base-content/50">
          {t("contacts.count", { ns: FANCALL_NS, count: contacts.length })}
        </p>
      </div>

      {/* Letter index along the right edge */}
      {sections.length > 1 && (
        <nav className="absolute right-0.5 top-1/2 z-20 flex -translate-y-1/2 flex-col items-center">
          {sections.map((section) => (
            <button
              key={section.letter}
              type="button"
              onClick={() => scrollToLetter(section.letter)}
              className="px-1 text-label-s font-semibold leading-4 text-primary"
            >
              {section.letter}
            </button>
          ))}
        </nav>
      )}
    </div>
  );
}
