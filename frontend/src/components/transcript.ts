/**
 * Lines the agent sends on the "fancall.transcript" data topic as the call goes.
 * The host app stores them per signed-in fan and trainee and passes them back
 * as `memory` when it dispatches the next call.
 */
import type { MemoryLine } from "@/schemas";

export const TRANSCRIPT_TOPIC = "fancall.transcript";

/** Decode one data packet; null when it is not a well-formed line. */
export function parseTranscriptLine(payload: Uint8Array): MemoryLine | null {
  try {
    const value: unknown = JSON.parse(new TextDecoder().decode(payload));
    if (typeof value !== "object" || value === null) return null;
    const { speaker, text } = value as Record<string, unknown>;
    if ((speaker !== "fan" && speaker !== "idol") || typeof text !== "string") {
      return null;
    }
    return text.trim() ? { speaker, text } : null;
  } catch {
    return null;
  }
}
