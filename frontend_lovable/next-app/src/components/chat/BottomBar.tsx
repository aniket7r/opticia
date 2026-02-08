"use client";

import { useState, useRef, useEffect, useCallback, type ReactNode } from "react";
import { Plus, ArrowUp, Mic, Music, Monitor, ImagePlus, Camera, Volume2, VolumeX, Video, VideoOff, X, Wrench, Globe, FlaskConical } from "lucide-react";
import { cn } from "@/lib/utils";
import { useVoiceRecording } from "@/hooks/useVoiceRecording";
import { VoiceRecording } from "./VoiceRecording";
import { AttachmentPreview, type Attachment } from "./AttachmentPreview";
import { toast } from "sonner";

type ActiveTool = "web-search" | "deep-research" | null;

const TOOL_CONFIG: Record<Exclude<ActiveTool, null>, { icon: ReactNode; label: string }> = {
  "web-search": { icon: <Globe className="h-3.5 w-3.5" />, label: "Web search" },
  "deep-research": { icon: <FlaskConical className="h-3.5 w-3.5" />, label: "Deep research" },
};

interface BottomBarProps {
  speakerOn: boolean;
  cameraOn: boolean;
  onToggleSpeaker: () => void;
  onToggleCamera: () => void;
  onSendMessage: (text: string, attachments?: Attachment[]) => void;
  onCapturePhoto: () => string | null;
  onScreenShare?: () => void;
  isScreenSharing?: boolean;
  isVoiceStreaming?: boolean;
  onToggleVoice?: () => void;
}

export function BottomBar({
  speakerOn,
  cameraOn,
  onToggleSpeaker,
  onToggleCamera,
  onSendMessage,
  onCapturePhoto,
  onScreenShare,
  isScreenSharing,
  isVoiceStreaming,
  onToggleVoice,
}: BottomBarProps) {
  const [text, setText] = useState("");
  const [plusOpen, setPlusOpen] = useState(false);
  const [mediaOpen, setMediaOpen] = useState(false);
  const [toolsOpen, setToolsOpen] = useState(false);
  const [activeTool, setActiveTool] = useState<ActiveTool>(null);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const voiceRecording = useVoiceRecording({
    onRecordingComplete: (blob) => {
      toast("Voice message recorded");
      console.log("Voice recording blob:", blob.size, "bytes");
    },
  });

  const hasText = text.trim().length > 0;
  const hasContent = hasText || attachments.length > 0;

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 140) + "px";
    }
  }, [text]);

  const handleSend = () => {
    if (!hasContent) return;
    onSendMessage(text.trim(), attachments.length > 0 ? attachments : undefined);
    setText("");
    setAttachments([]);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileSelect = () => {
    setPlusOpen(false);
    fileInputRef.current?.click();
  };

  const handleFileSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    
    Array.from(files).forEach((file) => {
      const isImage = file.type.startsWith("image/");
      if (isImage) {
        const reader = new FileReader();
        reader.onload = () => {
          setAttachments((prev) => [...prev, {
            id: `file-${Date.now()}-${Math.random()}`,
            name: file.name,
            type: "image",
            preview: reader.result as string,
          }]);
        };
        reader.readAsDataURL(file);
      } else {
        setAttachments((prev) => [...prev, {
          id: `file-${Date.now()}-${Math.random()}`,
          name: file.name,
          type: "file",
        }]);
      }
    });

    // Reset input so same file can be re-selected
    e.target.value = "";
  };

  const handleCapturePhoto = useCallback(() => {
    setPlusOpen(false);
    const dataUrl = onCapturePhoto();
    if (dataUrl) {
      setAttachments((prev) => [...prev, {
        id: `photo-${Date.now()}`,
        name: "Camera photo",
        type: "image",
        preview: dataUrl,
      }]);
      toast("Photo captured");
    } else {
      toast.error("Camera not available");
    }
  }, [onCapturePhoto]);

  const removeAttachment = useCallback((id: string) => {
    setAttachments((prev) => prev.filter((a) => a.id !== id));
  }, []);

  const closeMenus = () => {
    setPlusOpen(false);
    setMediaOpen(false);
    setToolsOpen(false);
  };

  // Only show local voice recording UI if live streaming is not available
  if (voiceRecording.recording && !onToggleVoice) {
    return (
      <div className="px-4 pb-[env(safe-area-inset-bottom,12px)] pt-3">
        <div className="rounded-2xl border border-border bg-card p-3 shadow-sm">
          <VoiceRecording
            onStop={voiceRecording.stopRecording}
            audioLevel={voiceRecording.audioLevel}
            duration={voiceRecording.duration}
          />
        </div>
      </div>
    );
  }

  return (
    <>
      {(plusOpen || mediaOpen || toolsOpen) && (
        <div className="fixed inset-0 z-30" onClick={closeMenus} aria-hidden="true" />
      )}

      <div className="pb-[max(env(safe-area-inset-bottom,12px),16px)] pt-1">
        <div className="w-full">
        <div className="relative rounded-2xl border border-border bg-card shadow-sm transition-shadow duration-300 focus-within:shadow-md focus-within:border-foreground/15">
          {/* Attachment previews */}
          <AttachmentPreview attachments={attachments} onRemove={removeAttachment} />

          {/* Active tool badge */}
          {activeTool && (
            <div className="px-3 pt-2.5">
              <button
                onClick={() => setActiveTool(null)}
                className="group inline-flex items-center gap-1.5 rounded-full bg-accent px-2.5 py-1 text-xs font-medium text-foreground transition-colors hover:bg-destructive/15 hover:text-destructive"
                aria-label={`Remove ${TOOL_CONFIG[activeTool].label}`}
              >
                <span className="group-hover:hidden">{TOOL_CONFIG[activeTool].icon}</span>
                <X className="hidden h-3.5 w-3.5 group-hover:block" />
                <span>{TOOL_CONFIG[activeTool].label}</span>
              </button>
            </div>
          )}

          {/* Textarea */}
          <textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={closeMenus}
            placeholder="Type a message..."
            rows={1}
            className={cn(
              "w-full resize-none bg-transparent px-4 pt-3.5 pb-1.5 text-sm text-foreground leading-relaxed",
              "placeholder:text-muted-foreground/60",
              "focus:outline-none",
              "max-h-[140px]"
            )}
            aria-label="Message input"
          />

          {/* Bottom toolbar */}
          <div className="flex items-center gap-0.5 px-2 pb-2 pt-0.5">
            {/* Plus button */}
            <div className="relative">
              <button
                onClick={() => { setMediaOpen(false); setToolsOpen(false); setPlusOpen((o) => !o); }}
                className={cn(
                  "flex items-center justify-center rounded-lg p-1.5 transition-all duration-200 active:scale-90",
                  plusOpen ? "bg-foreground text-background" : "text-muted-foreground hover:text-foreground hover:bg-accent"
                )}
                aria-label="Attachments"
                aria-expanded={plusOpen}
              >
                <Plus className={cn("h-4 w-4 transition-transform duration-200", plusOpen && "rotate-45")} />
              </button>

              {plusOpen && (
                <div className="absolute bottom-full left-0 z-50 mb-2 w-52 origin-bottom-left animate-scale-in rounded-xl border border-border bg-card shadow-lg">
                  <div className="p-1.5">
                    <MenuButton icon={<Monitor className="h-4 w-4" />} label={isScreenSharing ? "Stop sharing" : "Share screen"} onClick={() => { setPlusOpen(false); onScreenShare?.(); }} />
                    <MenuButton icon={<ImagePlus className="h-4 w-4" />} label="Add from files" onClick={handleFileSelect} />
                    <MenuButton icon={<Camera className="h-4 w-4" />} label="Capture photo" onClick={handleCapturePhoto} />
                  </div>
                </div>
              )}
            </div>

            {/* Media button */}
            <div className="relative">
              <button
                onClick={() => { setPlusOpen(false); setToolsOpen(false); setMediaOpen((o) => !o); }}
                className={cn(
                  "flex items-center justify-center rounded-lg p-1.5 transition-all duration-200 active:scale-90",
                  mediaOpen ? "bg-foreground text-background" : "text-muted-foreground hover:text-foreground hover:bg-accent"
                )}
                aria-label="Media controls"
                aria-expanded={mediaOpen}
              >
                <Music className="h-4 w-4" />
              </button>

              {mediaOpen && (
                <div className="absolute bottom-full left-0 z-50 mb-2 w-52 origin-bottom-left animate-scale-in rounded-xl border border-border bg-card shadow-lg">
                  <div className="p-1.5">
                    <MenuButton
                      icon={speakerOn ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4 text-destructive" />}
                      label={speakerOn ? "Speaker on" : "Speaker off"}
                      onClick={() => { onToggleSpeaker(); setMediaOpen(false); }}
                    />
                    <MenuButton
                      icon={cameraOn ? <Video className="h-4 w-4" /> : <VideoOff className="h-4 w-4 text-destructive" />}
                      label={cameraOn ? "Camera on" : "Camera off"}
                      onClick={() => { onToggleCamera(); setMediaOpen(false); }}
                    />
                    <MenuButton
                      icon={<Mic className="h-4 w-4" />}
                      label="Microphone"
                      onClick={() => {
                        if (voiceRecording.recording) voiceRecording.stopRecording();
                        else voiceRecording.startRecording();
                        setMediaOpen(false);
                      }}
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Tools button */}
            <div className="relative">
              <button
                onClick={() => { setPlusOpen(false); setMediaOpen(false); setToolsOpen((o) => !o); }}
                className={cn(
                  "flex items-center justify-center rounded-lg p-1.5 transition-all duration-200 active:scale-90",
                  toolsOpen ? "bg-foreground text-background" : "text-muted-foreground hover:text-foreground hover:bg-accent"
                )}
                aria-label="Tools"
                aria-expanded={toolsOpen}
              >
                <Wrench className="h-4 w-4" />
              </button>

              {toolsOpen && (
                <div className="absolute bottom-full left-0 z-50 mb-2 w-52 origin-bottom-left animate-scale-in rounded-xl border border-border bg-card shadow-lg">
                  <div className="p-1.5">
                    <MenuButton icon={<Globe className="h-4 w-4" />} label="Web search" onClick={() => { setToolsOpen(false); setActiveTool((t) => t === "web-search" ? null : "web-search"); }} />
                    <MenuButton icon={<FlaskConical className="h-4 w-4" />} label="Deep research" onClick={() => { setToolsOpen(false); setActiveTool((t) => t === "deep-research" ? null : "deep-research"); }} />
                  </div>
                </div>
              )}
            </div>

            <div className="flex-1" />

            {/* Mic - live voice streaming to Gemini */}
            <button
              onClick={onToggleVoice || voiceRecording.startRecording}
              className={cn(
                "flex items-center justify-center rounded-lg p-1.5 transition-all duration-200 active:scale-90",
                isVoiceStreaming
                  ? "text-red-500 bg-red-500/10"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent"
              )}
              aria-label={isVoiceStreaming ? "Stop voice" : "Start voice"}
            >
              <Mic className={cn("h-4 w-4", isVoiceStreaming && "animate-pulse")} />
            </button>

            {/* Send */}
            <button
              onClick={handleSend}
              disabled={!hasContent}
              className={cn(
                "flex items-center justify-center rounded-lg p-1.5 transition-all duration-200 active:scale-90",
                hasContent ? "bg-foreground text-background shadow-sm" : "text-muted-foreground/30 cursor-default"
              )}
              aria-label="Send message"
            >
              <ArrowUp className="h-4 w-4" />
            </button>
          </div>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept="image/*,.pdf,.doc,.docx,.txt"
          multiple
          onChange={handleFileSelected}
        />
        </div>
      </div>
    </>
  );
}

function MenuButton({ icon, label, onClick }: { icon: React.ReactNode; label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors duration-150 text-foreground hover:bg-accent active:bg-accent/80"
    >
      <span className="text-muted-foreground">{icon}</span>
      <span>{label}</span>
    </button>
  );
}
