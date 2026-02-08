"use client";

import { cn } from "@/lib/utils";

type ProactivityLevel = "low" | "medium" | "high";

interface ProactivitySelectorProps {
  current: ProactivityLevel;
  onChange: (level: ProactivityLevel) => void;
}

const descriptions: Record<ProactivityLevel, string> = {
  low: "AI answers only when asked",
  medium: "AI offers occasional suggestions",
  high: "AI actively guides and corrects",
};

export function ProactivitySelector({ current, onChange }: ProactivitySelectorProps) {
  return (
    <div className="px-4 py-3">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-base">🎚️</span>
        <span className="text-sm font-medium text-foreground">Proactivity</span>
      </div>

      <div className="flex gap-1 rounded-lg bg-muted p-1">
        {(["low", "medium", "high"] as const).map((level) => (
          <button
            key={level}
            onClick={() => onChange(level)}
            className={cn(
              "flex-1 rounded-md py-2 px-3 text-xs font-medium capitalize transition-colors",
              current === level
                ? "bg-primary text-primary-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            )}
            aria-label={`Set proactivity to ${level}`}
            aria-pressed={current === level}
          >
            {level}
          </button>
        ))}
      </div>

      <p className="mt-2 text-xs text-muted-foreground">{descriptions[current]}</p>
    </div>
  );
}
