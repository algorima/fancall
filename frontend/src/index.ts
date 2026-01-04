/**
 * Fancall module - LiveKit-based video call functionality
 * Reusable LiveKit integration for voice-enabled AI agents
 *
 * Entry points:
 * - "fancall" (this file): Server-safe infrastructure (Repository, types, schemas, i18n)
 * - "fancall/client": Client-only components (AgentCall, StartCallSection)
 *
 * Design Philosophy:
 * Following aioia-core and React RFC #227 pattern:
 * - Main entry exports server-safe code (no React hooks)
 * - Client entry exports UI components with 'use client' directive
 */

// Repository (server-safe, no React hooks)
export { LiveRoomRepository } from "./repositories/LiveRoomRepository";

// Types & Schemas (server-safe)
export type {
  LiveRoom,
  TokenResponse,
  DispatchResponse,
  AgentDispatchRequest,
} from "./schemas";
export {
  liveRoomSchema,
  tokenResponseSchema,
  dispatchResponseSchema,
} from "./schemas";

// i18n - Server-safe exports (JSON resources and constants)
export { FANCALL_NS, fancallTranslations } from "./i18n/translations";
