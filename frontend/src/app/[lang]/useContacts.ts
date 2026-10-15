"use client";

import { useEffect, useState } from "react";

import { type Contact, contactListSchema } from "@/schemas";

/**
 * Local contact list (gitignored), e.g. idol photos and Simli face IDs that
 * must not be published with this public repo
 */
const CONTACTS_URL = "/contacts.local.json";

/** Single contact from the env vars used before the contacts list existed */
const envContact = (fallbackName: string): Contact[] => {
  const photoUrl = process.env.NEXT_PUBLIC_FANCALL_AVATAR_URL;
  if (!photoUrl) return [];
  return [
    {
      id: "default",
      name: process.env.NEXT_PUBLIC_FANCALL_DISPLAY_NAME || fallbackName,
      photoUrl,
    },
  ];
};

const fetchContacts = async (fallbackName: string): Promise<Contact[]> => {
  const response = await fetch(CONTACTS_URL, { cache: "no-store" });
  // No local list is expected on a fresh checkout
  if (response.status === 404) return envContact(fallbackName);
  if (!response.ok) {
    throw new Error(`Failed to load contacts: HTTP ${response.status}`);
  }
  return contactListSchema.parse(await response.json());
};

/** Contacts to call; null while loading */
export const useContacts = (fallbackName: string) => {
  const [contacts, setContacts] = useState<Contact[] | null>(null);

  useEffect(() => {
    let isCurrent = true;
    void fetchContacts(fallbackName).then((list) => {
      if (isCurrent) setContacts(list);
    });
    return () => {
      isCurrent = false;
    };
  }, [fallbackName]);

  return contacts;
};
