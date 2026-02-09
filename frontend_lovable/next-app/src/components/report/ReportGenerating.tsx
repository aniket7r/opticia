"use client";

import { FileText } from "lucide-react";

interface ReportGeneratingProps {
  topic: string;
  estimatedSeconds?: number;
}

export function ReportGenerating({ topic, estimatedSeconds = 15 }: ReportGeneratingProps) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 p-6">
      {/* Animated icon */}
      <div className="relative">
        <div className="absolute inset-0 animate-ping rounded-full bg-primary/20" />
        <div className="relative flex h-14 w-14 items-center justify-center rounded-full bg-primary/10">
          <FileText className="h-7 w-7 text-primary animate-pulse" />
        </div>
      </div>

      <div className="text-center space-y-1.5">
        <p className="text-sm font-medium text-foreground">Generating report</p>
        <p className="text-xs text-muted-foreground max-w-[200px] truncate">{topic}</p>
      </div>

      {/* Shimmer progress bar */}
      <div className="w-48 h-1.5 rounded-full bg-muted overflow-hidden">
        <div
          className="h-full rounded-full bg-gradient-to-r from-primary/60 via-primary to-primary/60 animate-shimmer"
          style={{
            backgroundSize: "200% 100%",
            animation: `shimmer ${estimatedSeconds}s linear infinite`,
          }}
        />
      </div>

      <p className="text-[11px] text-muted-foreground">~{estimatedSeconds}s</p>

      <style jsx>{`
        @keyframes shimmer {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
      `}</style>
    </div>
  );
}
