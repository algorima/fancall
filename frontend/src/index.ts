/**
 * Fancall module - LiveKit-based video call functionality
 * Reusable LiveKit integration for voice-enabled AI agents
 */

// Types and Schemas
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

// Components
export { AgentCall } from "./components/AgentCall";
export type { AgentCallProps } from "./components/AgentCall";
export { StartCallSection } from "./components/StartCallSection";
export type { StartCallSectionProps } from "./components/StartCallSection";

// Repositories
export { LiveRoomRepository } from "./repositories/LiveRoomRepository";

// i18n - Export namespace constant and translations for library integration
// Note: These exports are from a server-safe module (no React dependencies)
export { FANCALL_NS, fancallTranslations } from "./i18n/translations";
