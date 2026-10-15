"use client";

import clsx from "clsx";
import { useCallback, useEffect, useRef, useState } from "react";

import { type ClipMode, pickNextClip } from "@/components/clipGraph";
import type { ClipGraph, GraphClip } from "@/schemas";

export interface ClipGraphPlayerProps {
  graph: ClipGraph;
  mode: ClipMode;
  className?: string;
}

type Slots = [GraphClip | null, GraphClip | null];

/**
 * 앵커 포즈에서 시작해 앵커 포즈로 끝나는 짧은 클립을 이어 재생합니다.
 * 영상 두 개를 번갈아 쓰며, 다음 클립을 미리 불러 두었다가 끝 프레임에서 바로 넘깁니다.
 * 이어지는 두 클립의 경계 프레임이 같은 앵커 포즈라 끊김 없이 이어집니다.
 */
export function ClipGraphPlayer({
  graph,
  mode,
  className,
}: ClipGraphPlayerProps) {
  const videoA = useRef<HTMLVideoElement>(null);
  const videoB = useRef<HTMLVideoElement>(null);
  const [slots, setSlots] = useState<Slots>([null, null]);
  const [active, setActive] = useState<0 | 1>(0);
  const modeRef = useRef(mode);
  modeRef.current = mode;

  // Start on the main anchor once mounted (random picks must not run on the server)
  useEffect(() => {
    const first = pickNextClip(graph, graph.anchors[0], modeRef.current, null);
    const next =
      first && pickNextClip(graph, first.to, modeRef.current, first.id);
    setSlots([first, next]);
    setActive(0);
  }, [graph]);

  // A mode change re-plans the queued clip so the reaction matches right away
  useEffect(() => {
    setSlots((current) => {
      const playing = current[active];
      if (!playing) return current;
      const next = pickNextClip(graph, playing.to, mode, playing.id);
      const updated: Slots = [...current];
      updated[active === 0 ? 1 : 0] = next;
      return updated;
    });
  }, [mode, graph, active]);

  const handleEnded = useCallback(
    (slot: 0 | 1) => {
      if (slot !== active) return;
      const nextSlot = slot === 0 ? 1 : 0;
      const nextClip = slots[nextSlot];
      const nextVideo = (nextSlot === 0 ? videoA : videoB).current;
      if (!nextClip || !nextVideo) {
        // Nothing queued: replay this clip, which ends where it started
        void (slot === 0 ? videoA : videoB).current?.play();
        return;
      }
      void nextVideo.play();
      setActive(nextSlot);
      setSlots((current) => {
        const updated: Slots = [...current];
        updated[slot] = pickNextClip(
          graph,
          nextClip.to,
          modeRef.current,
          nextClip.id,
        );
        return updated;
      });
    },
    [active, slots, graph],
  );

  return (
    <div className={clsx("relative overflow-hidden", className)}>
      {([videoA, videoB] as const).map((ref, index) => {
        const clip = slots[index];
        return (
          <video
            key={index}
            ref={ref}
            src={clip?.url}
            muted
            playsInline
            preload="auto"
            autoPlay={index === active}
            onEnded={() => handleEnded(index as 0 | 1)}
            className={clsx(
              "absolute inset-0 size-full object-cover transition-opacity duration-75",
              index === active ? "opacity-100" : "opacity-0",
            )}
          />
        );
      })}
    </div>
  );
}
