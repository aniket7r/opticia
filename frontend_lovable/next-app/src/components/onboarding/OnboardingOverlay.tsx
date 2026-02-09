"use client";

import { useState, useCallback } from "react";
import Image from "next/image";
import { Mic, Camera as CameraIcon, Video, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

type OnboardingStep = "welcome" | "mic" | "camera" | "ready";

interface OnboardingOverlayProps {
  onComplete: () => void;
  onRequestMic: () => Promise<boolean>;
  onRequestCamera: () => Promise<boolean>;
}

export function OnboardingOverlay({ onComplete, onRequestMic, onRequestCamera }: OnboardingOverlayProps) {
  const [step, setStep] = useState<OnboardingStep>("welcome");
  const [micGranted, setMicGranted] = useState(false);
  const [cameraGranted, setCameraGranted] = useState(false);
  const [requesting, setRequesting] = useState(false);

  const handleRequestMic = useCallback(async () => {
    setRequesting(true);
    const granted = await onRequestMic();
    setMicGranted(granted);
    setRequesting(false);
    if (granted) {
      setStep("camera");
    }
  }, [onRequestMic]);

  const handleRequestCamera = useCallback(async () => {
    setRequesting(true);
    const granted = await onRequestCamera();
    setCameraGranted(granted);
    setRequesting(false);
    setStep("ready");
  }, [onRequestCamera]);

  const handleSkipMic = () => setStep("camera");
  const handleSkipCamera = () => setStep("ready");

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-background">
      <div className="mx-auto flex max-w-md flex-col items-center px-6 text-center animate-fade-in">
        {step === "welcome" && (
          <>
            <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-full overflow-hidden">
              <Image src="/logo.svg" alt="Opticia" width={80} height={80} />
            </div>
            <h1 className="mb-3 text-2xl font-bold text-foreground">
              Hi, I'm Opticia
            </h1>
            <p className="mb-2 text-base text-muted-foreground leading-relaxed">
              I can <strong>see</strong> what you're looking at and guide you through anything — hands-free.
            </p>
            <p className="mb-8 text-sm text-muted-foreground">
              Point your camera, ask me anything, and I'll walk you through it step by step.
            </p>
            <button
              onClick={() => setStep("mic")}
              className="flex items-center gap-2 rounded-full bg-primary px-8 py-3 text-base font-medium text-primary-foreground transition-default hover:bg-primary/90 active:scale-95"
            >
              Let's get started
              <ArrowRight className="h-4 w-4" />
            </button>
          </>
        )}

        {step === "mic" && (
          <>
            <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-primary/10">
              <Mic className="h-10 w-10 text-primary" />
            </div>
            <h2 className="mb-3 text-xl font-bold text-foreground">
              Talk to me naturally
            </h2>
            <p className="mb-8 text-sm text-muted-foreground leading-relaxed">
              I'll listen and respond with voice — perfect for when your hands are busy. You can also type if you prefer.
            </p>
            <button
              onClick={handleRequestMic}
              disabled={requesting}
              className="mb-3 flex w-full items-center justify-center gap-2 rounded-full bg-primary px-8 py-3 text-base font-medium text-primary-foreground transition-default hover:bg-primary/90 active:scale-95 disabled:opacity-60"
            >
              {requesting ? (
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
              ) : (
                <>
                  <Mic className="h-4 w-4" />
                  Enable microphone
                </>
              )}
            </button>
            <button
              onClick={handleSkipMic}
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Skip for now
            </button>
          </>
        )}

        {step === "camera" && (
          <>
            <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-primary/10">
              <Video className="h-10 w-10 text-primary" />
            </div>
            <h2 className="mb-3 text-xl font-bold text-foreground">
              Show me what you see
            </h2>
            <p className="mb-8 text-sm text-muted-foreground leading-relaxed">
              Point your camera at anything — a leaky pipe, a recipe, a math problem — and I'll understand what I'm looking at.
            </p>
            <button
              onClick={handleRequestCamera}
              disabled={requesting}
              className="mb-3 flex w-full items-center justify-center gap-2 rounded-full bg-primary px-8 py-3 text-base font-medium text-primary-foreground transition-default hover:bg-primary/90 active:scale-95 disabled:opacity-60"
            >
              {requesting ? (
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
              ) : (
                <>
                  <CameraIcon className="h-4 w-4" />
                  Enable camera
                </>
              )}
            </button>
            <button
              onClick={handleSkipCamera}
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Skip for now
            </button>

            {micGranted && (
              <p className="mt-4 text-xs text-success">✓ Microphone enabled</p>
            )}
          </>
        )}

        {step === "ready" && (
          <>
            <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-full overflow-hidden">
              <Image src="/logo.svg" alt="Opticia" width={80} height={80} />
            </div>
            <h2 className="mb-3 text-xl font-bold text-foreground">
              You're all set!
            </h2>
            <div className="mb-6 flex flex-col gap-2 text-sm">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Mic className={cn("h-4 w-4", micGranted ? "text-success" : "text-muted-foreground")} />
                <span>{micGranted ? "Microphone enabled" : "Microphone skipped — you can type instead"}</span>
              </div>
              <div className="flex items-center gap-2 text-muted-foreground">
                <Video className={cn("h-4 w-4", cameraGranted ? "text-success" : "text-muted-foreground")} />
                <span>{cameraGranted ? "Camera enabled" : "Camera skipped — you can share photos"}</span>
              </div>
            </div>
            <button
              onClick={onComplete}
              className="flex items-center gap-2 rounded-full bg-primary px-8 py-3 text-base font-medium text-primary-foreground transition-default hover:bg-primary/90 active:scale-95"
            >
              Start chatting
              <ArrowRight className="h-4 w-4" />
            </button>
          </>
        )}

        {/* Progress dots */}
        <div className="mt-8 flex gap-2">
          {(["welcome", "mic", "camera", "ready"] as OnboardingStep[]).map((s) => (
            <div
              key={s}
              className={cn(
                "h-2 rounded-full transition-all duration-300",
                s === step ? "w-6 bg-primary" : "w-2 bg-muted"
              )}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
