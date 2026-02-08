"use client";

import { useState, useRef, useCallback, useEffect } from "react";

type CameraFacing = "user" | "environment";

interface UseCameraOptions {
  autoStart?: boolean;
}

export function useCamera({ autoStart = false }: UseCameraOptions = {}) {
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [active, setActive] = useState(false);
  const [facing, setFacing] = useState<CameraFacing>("environment");
  const [error, setError] = useState<string | null>(null);
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  const stopStream = useCallback(() => {
    if (stream) {
      stream.getTracks().forEach((t) => t.stop());
      setStream(null);
    }
    setActive(false);
  }, [stream]);

  const startCamera = useCallback(async (facingMode: CameraFacing = facing) => {
    try {
      // Stop existing stream
      if (stream) {
        stream.getTracks().forEach((t) => t.stop());
      }
      setError(null);

      const newStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: facingMode === "user" ? "user" : { ideal: "environment" } },
        audio: false,
      });

      setStream(newStream);
      setActive(true);
      setFacing(facingMode);
      setHasPermission(true);

      if (videoRef.current) {
        videoRef.current.srcObject = newStream;
      }
    } catch (err: any) {
      console.error("Camera error:", err);
      if (err.name === "NotAllowedError") {
        setError("Camera permission denied");
        setHasPermission(false);
      } else if (err.name === "NotFoundError") {
        setError("No camera found");
      } else {
        setError("Camera unavailable");
      }
      setActive(false);
    }
  }, [facing, stream]);

  const flipCamera = useCallback(async () => {
    const newFacing = facing === "user" ? "environment" : "user";
    await startCamera(newFacing);
  }, [facing, startCamera]);

  const toggleCamera = useCallback(async () => {
    if (active) {
      stopStream();
    } else {
      await startCamera(facing);
    }
  }, [active, facing, startCamera, stopStream]);

  // Capture a photo from the current video stream
  const capturePhoto = useCallback((): string | null => {
    if (!videoRef.current || !active) return null;
    const video = videoRef.current;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;
    ctx.drawImage(video, 0, 0);
    return canvas.toDataURL("image/jpeg", 0.85);
  }, [active]);

  // Attach stream to video element
  const attachVideo = useCallback((el: HTMLVideoElement | null) => {
    videoRef.current = el;
    if (el && stream) {
      el.srcObject = stream;
    }
  }, [stream]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (stream) {
        stream.getTracks().forEach((t) => t.stop());
      }
    };
  }, [stream]);

  // Auto-start
  useEffect(() => {
    if (autoStart) {
      startCamera();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return {
    active,
    facing,
    error,
    hasPermission,
    stream,
    startCamera,
    stopStream,
    flipCamera,
    toggleCamera,
    attachVideo,
    capturePhoto,
  };
}
