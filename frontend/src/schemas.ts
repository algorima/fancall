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

/** One line from an earlier call between this fan and this trainee */
export interface MemoryLine {
  speaker: "fan" | "idol";
  text: string;
}

/**
 * Agent dispatch request payload
 * Generic specification for LiveKit agent dispatch
 */
export interface AgentDispatchRequest {
  avatarId?: string | null;
  profilePictureUrl?: string | null;
  voiceId?: string | null;
  systemPrompt?: string | null;
  /** Fan's app language (e.g. "en"); the idol greets in it before the fan speaks */
  language?: string | null;
  /**
   * Id of the trainee this call is with. For a signed-in fan, fancall loads the
   * stored lines of earlier calls under this key when `memory` is not passed
   */
  memoryKey?: string | null;
  /** Lines of earlier calls with this trainee, oldest first (max 200, 500 chars each) */
  memory?: MemoryLine[];
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

export const clipKindSchema = z.enum([
  "listen",
  "nod",
  "smile",
  "tilt",
  "think",
  "surprise",
  "talk",
  "bye",
]);

export type ClipKind = z.infer<typeof clipKindSchema>;

/** A short pre-rendered clip that starts on one anchor pose and ends on one */
export const graphClipSchema = z.object({
  id: z.string().min(1),
  url: z.string().min(1),
  from: z.string().min(1),
  to: z.string().min(1),
  kind: clipKindSchema,
});

export type GraphClip = z.infer<typeof graphClipSchema>;

/**
 * Clip graph: anchor poses are nodes and clips are edges between them. The
 * first anchor is the main (front) pose the graph keeps returning to.
 */
export const clipGraphSchema = z
  .object({
    anchors: z.array(z.string().min(1)).min(1),
    clips: z.array(graphClipSchema).min(1),
  })
  .refine(
    (graph) =>
      graph.clips.every(
        (clip) =>
          graph.anchors.includes(clip.from) && graph.anchors.includes(clip.to),
      ),
    { message: "Every clip must start and end on a listed anchor" },
  );

export type ClipGraph = z.infer<typeof clipGraphSchema>;

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
  /** Pre-rendered reaction clips played on the device instead of a live avatar */
  clipGraph: clipGraphSchema.nullish(),
});

export type Contact = z.infer<typeof contactSchema>;

export const contactListSchema = z.array(contactSchema);
