import type { ClipGraph, ClipKind, GraphClip } from "@/schemas";

/** What the idol is doing, driving which clips may play next */
export type ClipMode = "listening" | "thinking" | "speaking" | "closing";

/**
 * Relative weight of each clip kind per mode. The listening mix follows real
 * 1:1 idol video calls: constant small reactions rather than a frozen face.
 */
const KIND_WEIGHTS: Record<ClipMode, Partial<Record<ClipKind, number>>> = {
  listening: { listen: 5, nod: 2, smile: 1.5, tilt: 1.5 },
  thinking: { nod: 3, think: 3, surprise: 1, listen: 1 },
  speaking: { talk: 1 },
  closing: { bye: 1 },
};

/** Fallback kinds when a mode has no clip from the current anchor */
const FALLBACK_KINDS: ClipKind[] = ["listen", "nod", "tilt", "smile"];

/**
 * Next clip to play from `anchor`. Every clip starts and ends on an anchor
 * pose, so any clip leaving the current anchor joins without a visible cut.
 * Prefers clips that lead back to the front anchor when leaving a tilt, and
 * avoids repeating the previous clip when there is a choice.
 */
export const pickNextClip = (
  graph: ClipGraph,
  anchor: string,
  mode: ClipMode,
  previousId: string | null,
  random: () => number = Math.random,
): GraphClip | null => {
  const fromAnchor = graph.clips.filter((clip) => clip.from === anchor);
  if (fromAnchor.length === 0) return null;

  const weights = KIND_WEIGHTS[mode];
  let candidates = fromAnchor.filter((clip) => weights[clip.kind]);
  if (candidates.length === 0) {
    candidates = fromAnchor.filter((clip) =>
      FALLBACK_KINDS.includes(clip.kind),
    );
  }
  if (candidates.length === 0) candidates = fromAnchor;
  if (candidates.length > 1) {
    const fresh = candidates.filter((clip) => clip.id !== previousId);
    if (fresh.length > 0) candidates = fresh;
  }

  const weightOf = (clip: GraphClip) => {
    const base = weights[clip.kind] ?? 1;
    // Drift back to the main anchor instead of wandering between tilts
    return clip.to === graph.anchors[0] ? base * 1.5 : base;
  };
  const total = candidates.reduce((sum, clip) => sum + weightOf(clip), 0);
  let roll = random() * total;
  for (const clip of candidates) {
    roll -= weightOf(clip);
    if (roll <= 0) return clip;
  }
  return candidates[candidates.length - 1];
};
