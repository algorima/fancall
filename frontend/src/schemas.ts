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
  /** Voice-only phone call over SIP (no avatar, speech input on). Defaults to false. */
  phoneCall?: boolean;
  /** First line spoken verbatim instead of an LLM-generated greeting. Applies to both video and phone calls. */
  openingMessage?: string | null;
}
