"use client";

import { useState, useRef, useCallback, useEffect } from "react";

interface UseScreenShareOptions {
  /** Called when screen share stops (including browser UI stop) */
  onStop?: () => void;
}

export function useScreenShare({ onStop }: UseScreenShareOptions = {}) {
  const [active, setActive] = useState(false);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Hidden video element for frame capture (independent of UI video element)
  const captureVideoRef = useRef<HTMLVideoElement | null>(null);
  const onStopRef = useRef(onStop);
  onStopRef.current = onStop;

  // Keep hidden video element in sync with stream
  useEffect(() => {
    if (!stream) {
      if (captureVideoRef.current) {
        captureVideoRef.current.srcObject = null;
      }
      return;
    }

    if (!captureVideoRef.current) {
      captureVideoRef.current = document.createElement("video");
      captureVideoRef.current.muted = true;
      captureVideoRef.current.playsInline = true;
    }

    captureVideoRef.current.srcObject = stream;
    captureVideoRef.current.play().catch(() => {});
  }, [stream]);

  const startScreenShare = useCallback(async (): Promise<boolean> => {
    try {
      setError(null);
      const displayStream = await navigator.mediaDevices.getDisplayMedia({
        video: true,
        audio: false,
      });

      // Listen for user stopping via browser UI
      displayStream.getVideoTracks()[0].onended = () => {
        setStream(null);
        setActive(false);
        onStopRef.current?.();
      };

      setStream(displayStream);
      setActive(true);
      return true;
    } catch (err: any) {
      console.error("Screen share error:", err);
      if (err.name === "NotAllowedError") {
        setError("Screen sharing cancelled");
      } else {
        setError("Screen sharing unavailable");
      }
      setActive(false);
      return false;
    }
  }, []);

  const stopScreenShare = useCallback(() => {
    if (stream) {
      stream.getTracks().forEach((t) => t.stop());
      setStream(null);
    }
    setActive(false);
  }, [stream]);

  const toggleScreenShare = useCallback(async () => {
    if (active) {
      stopScreenShare();
    } else {
      await startScreenShare();
    }
  }, [active, startScreenShare, stopScreenShare]);

  // Capture current screen frame as base64 JPEG (same pattern as camera.capturePhoto)
  const captureFrame = useCallback((): string | null => {
    const video = captureVideoRef.current;
    if (!video || !active) return null;
    if (video.videoWidth === 0 || video.videoHeight === 0) return null;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;
    ctx.drawImage(video, 0, 0);
    return canvas.toDataURL("image/jpeg", 0.7);
  }, [active]);

  useEffect(() => {
    return () => {
      if (stream) {
        stream.getTracks().forEach((t) => t.stop());
      }
    };
  }, [stream]);

  return {
    active,
    stream,
    error,
    startScreenShare,
    stopScreenShare,
    toggleScreenShare,
    captureFrame,
  };
}
