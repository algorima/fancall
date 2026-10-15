/**
 * Fancall Client-Only Exports
 *
 * This module contains all code that must run on the client side.
 * Import from 'fancall/client' to use these in your application.
 *
 * The 'use client' directive ensures this code is properly bundled
 * for client-side execution in React Server Components (RSC) environments.
 */

// Components (client-only)
export { AgentCall, MESSAGE_LIMIT_FALLBACK_MS } from "./components/AgentCall";
export type { AgentCallProps } from "./components/AgentCall";
export { StartCallSection } from "./components/StartCallSection";
export type { StartCallSectionProps } from "./components/StartCallSection";
export { IncomingCallScreen } from "./components/IncomingCallScreen";
export type { IncomingCallScreenProps } from "./components/IncomingCallScreen";
export { PhoneFrame } from "./components/PhoneFrame";
export type { PhoneFrameProps } from "./components/PhoneFrame";
export { ContactCard } from "./components/ContactCard";
export type { ContactCardProps } from "./components/ContactCard";
export { ContactsScreen } from "./components/ContactsScreen";
export type { ContactsScreenProps } from "./components/ContactsScreen";
export { LoadingQuips } from "./components/LoadingQuips";
export type { LoadingQuipsProps } from "./components/LoadingQuips";
