"use client";

import { useState, useRef, useCallback, useEffect } from "react";

export function useScreenShare() {
  const [active, setActive] = useState(false);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [error, setError] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  const startScreenShare = useCallback(async () => {
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
      };

      setStream(displayStream);
      setActive(true);

      if (videoRef.current) {
        videoRef.current.srcObject = displayStream;
      }
    } catch (err: any) {
      console.error("Screen share error:", err);
      if (err.name === "NotAllowedError") {
        setError("Screen sharing cancelled");
      } else {
        setError("Screen sharing unavailable");
      }
      setActive(false);
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

  const attachVideo = useCallback((el: HTMLVideoElement | null) => {
    videoRef.current = el;
    if (el && stream) {
      el.srcObject = stream;
    }
  }, [stream]);

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
    attachVideo,
  };
}
