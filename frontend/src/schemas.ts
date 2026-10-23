import type { BaseRecord } from "@aioia/core";
import { z } from "zod";

/**
 * LiveRoom schema matching backend response
 */
export const liveRoomSchema = z.object({
  id: z.string(),
  createdAt: z.string(),
  updatedAt: z.string(),
});

export interface LiveRoom extends BaseRecord {
  id: string;
  createdAt: string;
  updatedAt: string;
}

/**
 * Token response schema from POST /live-rooms/{id}/token
 */
export const tokenResponseSchema = z.object({
  token: z.string(),
  roomName: z.string(),
  identity: z.string(),
});

export type TokenResponse = z.infer<typeof tokenResponseSchema>;

/**
 * Dispatch response schema from POST /live-rooms/{id}/dispatch
 */
export const dispatchResponseSchema = z.object({
  dispatchId: z.string(),
  roomName: z.string(),
  agentName: z.string(),
});

export type DispatchResponse = z.infer<typeof dispatchResponseSchema>;

/**
 * Agent dispatch request payload
 * Generic specification for LiveKit agent dispatch
 */
export interface AgentDispatchRequest {
  avatarId?: string | null;
  profilePictureUrl?: string | null;
  /** ElevenLabs voice ID. A Fish Audio voice ID will fail TTS; omit to use the default voice. */
  voiceId?: string | null;
  systemPrompt?: string | null;
}

/**
 * Where the avatar's video sits inside the call photo, as fractions of the
 * photo's width and height. When set, the call screen lays the lip-synced
 * video over the same spot of the full-screen photo, so a square avatar
 * fills a tall phone without being zoomed in.
 */
export const videoRegionSchema = z.object({
  x: z.number().min(0).max(1),
  y: z.number().min(0).max(1),
  width: z.number().gt(0).max(1),
  height: z.number().gt(0).max(1),
});

export type VideoRegion = z.infer<typeof videoRegionSchema>;

/**
 * A callable idol in the contacts list
 */
export const contactSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  /** Profile photo: contacts list, contact card and the calling screens */
  photoUrl: z.string().min(1),
  /** Still the avatar is animated from, shown once the call connects */
  callPhotoUrl: z.string().min(1).nullish(),
  avatarId: z.string().nullish(),
  voiceId: z.string().nullish(),
  systemPrompt: z.string().nullish(),
  videoRegion: videoRegionSchema.nullish(),
});

export type Contact = z.infer<typeof contactSchema>;

export const contactListSchema = z.array(contactSchema);
