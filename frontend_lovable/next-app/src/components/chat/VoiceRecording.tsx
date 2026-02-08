"use client";

import { Square } from "lucide-react";
import { cn } from "@/lib/utils";

interface VoiceRecordingProps {
  onStop: () => void;
  audioLevel?: number;
  duration?: number;
}

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function VoiceRecording({ onStop, audioLevel = 0, duration = 0 }: VoiceRecordingProps) {
  // Generate bar heights from audio level
  const bars = 7;
  const barHeights = Array.from({ length: bars }, (_, i) => {
    const base = 8;
    const center = Math.abs(i - Math.floor(bars / 2));
    const centerBoost = 1 - center * 0.15;
    const jitter = Math.sin(Date.now() / 200 + i * 0.8) * 0.2;
    return base + audioLevel * 24 * centerBoost + jitter * 8;
  });

  return (
    <div className="flex items-center gap-3">
      {/* Audio level bars */}
      <div className="flex items-center gap-0.5 h-8">
        {barHeights.map((h, i) => (
          <div
            key={i}
            className="w-1 rounded-full bg-destructive transition-all duration-75"
            style={{ height: `${Math.max(4, h)}px` }}
          />
        ))}
      </div>

      {/* Duration */}
      <span className="min-w-[40px] text-sm font-mono text-destructive">
        {formatDuration(duration)}
      </span>

      <span className="flex-1 text-sm text-muted-foreground">Listening...</span>

      <button
        onClick={onStop}
        className="tap-target flex items-center justify-center rounded-full bg-destructive p-3 text-destructive-foreground transition-default hover:bg-destructive/90 active:scale-95"
        aria-label="Stop recording"
      >
        <Square className="h-4 w-4" />
      </button>
    </div>
  );
}
