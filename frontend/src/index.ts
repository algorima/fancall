/**
 * Fancall module - LiveKit-based video call functionality
 * Reusable LiveKit integration for voice-enabled AI agents
 *
 * Entry points:
 * - "fancall" (this file): Client-only components
 * - "fancall/schemas": Server/client safe types and schemas
 * - "fancall/locale": Server/client safe i18n resources
 */

// Components (client-only)
export { AgentCall } from "./components/AgentCall";
export type { AgentCallProps } from "./components/AgentCall";
export { StartCallSection } from "./components/StartCallSection";
export type { StartCallSectionProps } from "./components/StartCallSection";

// Repositories (client-only, uses React hooks)
export { LiveRoomRepository } from "./repositories/LiveRoomRepository";
