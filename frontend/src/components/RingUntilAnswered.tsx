"use client";

import { useVoiceAssistant } from "@livekit/components-react";

import { IncomingCallScreen } from "@/components/IncomingCallScreen";

interface RingUntilAnsweredProps {
  displayName: string;
  avatarUrl?: string | null;
  onDecline?: () => void;
}

/**
 * Keeps the "calling" screen up until the trainee can actually be seen.
 *
 * A real phone keeps ringing until the other side picks up, and their face is
 * there the moment it connects. Showing the call screen with "Connecting…" while
 * the agent and avatar start (8–13s in a 2026-10-23 local test) breaks that. The
 * naturalness criteria want the face within 3s of the call starting
 * (docs/call-naturalness-criteria.md).
 *
 * The call counts as answered once the avatar video arrives, or once the agent
 * speaks without one (voice-only fallback when the avatar fails to start).
 */
export function RingUntilAnswered({
  displayName,
  avatarUrl,
  onDecline,
}: RingUntilAnsweredProps) {
  const { state, videoTrack } = useVoiceAssistant();
  const answered = !!videoTrack || state === "speaking";

  if (answered) return null;

  return (
    <div className="absolute inset-0 z-50" data-testid="ring-until-answered">
      <IncomingCallScreen
        displayName={displayName}
        avatarUrl={avatarUrl}
        status="calling"
        onDecline={onDecline}
      />
    </div>
  );
}
