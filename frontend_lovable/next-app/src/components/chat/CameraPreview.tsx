"use client";

import { useEffect } from "react";
import { CameraOff, RefreshCw, Camera, VideoOff } from "lucide-react";
import { cn } from "@/lib/utils";
import type { useCamera } from "@/hooks/useCamera";

interface CameraPreviewProps {
  compact?: boolean;
  camera?: ReturnType<typeof useCamera>;
  screenShareStream?: MediaStream | null;
  onToggle?: () => void;
}

export function CameraPreview({ compact = false, camera, screenShareStream, onToggle }: CameraPreviewProps) {
  const isScreenSharing = !!screenShareStream;
  const cameraActive = camera?.active ?? false;
  const cameraError = camera?.error ?? null;

  // If screen sharing, show that feed
  if (isScreenSharing) {
    return (
      <div className="relative h-full w-full bg-secondary">
        <video
          ref={(el) => {
            if (el && screenShareStream) {
              el.srcObject = screenShareStream;
            }
          }}
          autoPlay
          playsInline
          muted
          className="h-full w-full object-contain"
        />
        <div className="absolute top-3 right-3 flex items-center gap-1.5 rounded-full bg-destructive/80 px-3 py-1 text-xs text-destructive-foreground backdrop-blur-sm">
          <div className="h-2 w-2 rounded-full bg-destructive-foreground animate-pulse" />
          Sharing screen
        </div>
      </div>
    );
  }

  // Camera error
  if (cameraError) {
    return (
      <div className="flex h-full w-full flex-col items-center justify-center gap-3 bg-secondary">
        <VideoOff className="h-8 w-8 text-destructive" />
        <p className="text-sm text-muted-foreground">{cameraError}</p>
        {camera && (
          <button
            onClick={() => camera.startCamera()}
            className="tap-target rounded-lg bg-primary px-4 py-2 text-sm text-primary-foreground transition-default hover:bg-primary/90 active:scale-95"
            aria-label="Retry camera"
          >
            Retry
          </button>
        )}
      </div>
    );
  }

  // Camera off
  if (!cameraActive) {
    return (
      <div
        className="flex h-full w-full flex-col items-center justify-center gap-2 bg-secondary cursor-pointer active:scale-95 transition-transform"
        onClick={onToggle}
        role="button"
        aria-label="Turn camera on"
      >
        <CameraOff className="h-8 w-8 text-muted-foreground" />
        <p className="text-xs text-muted-foreground">Tap to turn on</p>
      </div>
    );
  }

  // Active camera
  return (
    <div className="relative h-full w-full bg-secondary cursor-pointer" onClick={onToggle}>
      <video
        ref={camera?.attachVideo}
        autoPlay
        playsInline
        muted
        className={cn(
          "h-full w-full object-cover",
          camera?.facing === "user" && "scale-x-[-1]"
        )}
      />

      {/* Flip camera button - top right */}
      {camera && (
        <div className="absolute top-2 right-2 z-40">
          <button
            onClick={(e) => { e.stopPropagation(); camera.flipCamera(); }}
            className="rounded-full bg-foreground/20 p-1.5 backdrop-blur-sm transition-default hover:bg-foreground/30 active:scale-95"
            aria-label="Flip camera"
          >
            <RefreshCw className="h-3.5 w-3.5 text-white" />
          </button>
        </div>
      )}

      {/* Live indicator */}
      <div className="absolute top-3 left-3 flex items-center gap-1.5 rounded-full bg-foreground/10 px-2.5 py-1 text-xs text-white backdrop-blur-sm">
        <div className="h-2 w-2 rounded-full bg-success animate-pulse" />
        Live
      </div>
    </div>
  );
}
