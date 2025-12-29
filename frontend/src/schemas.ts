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
  idleVideoUrl?: string | null;
  voiceId?: string | null;
  systemPrompt?: string | null;
}
