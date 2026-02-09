"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { MonitorOff, WifiOff } from "lucide-react";
import { cn } from "@/lib/utils";
import { FloatingPiP } from "@/components/chat/FloatingPiP";
import { LargePreview } from "@/components/chat/LargePreview";
import { TaskProgressCard } from "@/components/task/TaskProgressCard";
import { ReportPanel } from "@/components/report/ReportPanel";

import { CameraPreview } from "@/components/chat/CameraPreview";
import { ChatMessages } from "@/components/chat/ChatMessages";
import { ChatHeader } from "@/components/chat/ChatHeader";
import { BottomBar } from "@/components/chat/BottomBar";
import { ChatSidebar } from "@/components/sidebar/ChatSidebar";
import { SearchOverlay } from "@/components/sidebar/SearchOverlay";
import { OnboardingOverlay } from "@/components/onboarding/OnboardingOverlay";
import { useCamera } from "@/hooks/useCamera";
import { useIsMobile } from "@/hooks/use-mobile";
import { useScreenShare } from "@/hooks/useScreenShare";
import { useChat, Message } from "@/hooks/useChat";
import { useWebSocket } from "@/providers/WebSocketProvider";
import { toast } from "sonner";
import type { ChatSummary } from "@/components/sidebar/types";

const ONBOARDING_KEY = "opticia-onboarded";
const CHATS_KEY = "opticia-chats";

const AppPageClient = () => {
  const isMobile = useIsMobile();

  // WebSocket connection
  const { isConnected, connectionState, sessionId } = useWebSocket();

  // Camera + screen share hooks (must be before useChat so captureFrame is available)
  const camera = useCamera();
  const screenShare = useScreenShare();

  // Stable capture function for useChat - captures frame from active video source
  const captureFrameRef = useRef<(() => string | null) | null>(null);
  captureFrameRef.current = () => {
    if (screenShare.active) {
      return screenShare.captureFrame();
    }
    if (camera.active) {
      return camera.capturePhoto();
    }
    return null;
  };
  const stableCaptureFrame = useCallback(() => captureFrameRef.current?.() ?? null, []);

  // Chat hook with real backend integration
  const {
    messages,
    isLoading,
    sendMessage,
    startVoiceInput,
    stopVoiceInput,
    startVideoStream,
    stopVideoStream,
    capturePhoto: sendPhotoToAI,
    clearChat,
    thinkingSteps,
    isThinking,
    taskTitle: chatTaskTitle,
    taskSteps: chatTaskSteps,
    isTaskActive,
    handleToggleStep: chatHandleToggleStep,
    dismissTask,
    reportData,
    isReportActive,
    dismissReport,
    send,
  } = useChat({
    onToolCall: (name, args) => {
      toast.info(`AI is using ${name}...`);
    },
    onError: (error) => {
      toast.error(error.message);
    },
    captureFrame: stableCaptureFrame,
  });

  // Local state - initialize as false, check localStorage in useEffect to avoid hydration mismatch
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [isHydrated, setIsHydrated] = useState(false);

  // Check onboarding status after hydration
  useEffect(() => {
    const hasOnboarded = localStorage.getItem(ONBOARDING_KEY);
    if (!hasOnboarded) {
      setShowOnboarding(true);
    }
    setIsHydrated(true);
  }, []);


  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Set sidebar state based on screen width after hydration
  useEffect(() => {
    setSidebarOpen(window.innerWidth >= 768);
  }, []);

  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const [speakerOn, setSpeakerOn] = useState(true);
  const [searchOpen, setSearchOpen] = useState(false);

  // Load chats from localStorage after hydration
  const [chats, setChats] = useState<ChatSummary[]>([]);

  useEffect(() => {
    const saved = localStorage.getItem(CHATS_KEY);
    if (saved) {
      try {
        setChats(JSON.parse(saved));
      } catch {
        // Invalid JSON, ignore
      }
    }
  }, []);

  // Save chats to localStorage
  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem(CHATS_KEY, JSON.stringify(chats));
    }
  }, [chats]);

  // Create new chat when session connects
  useEffect(() => {
    if (sessionId && !currentChatId) {
      const newChat: ChatSummary = {
        id: sessionId,
        title: "New conversation",
        status: "active",
        createdAt: new Date(),
        favorite: false,
      };
      setChats((prev) => {
        if (prev.some((c) => c.id === sessionId)) return prev;
        return [newChat, ...prev];
      });
      setCurrentChatId(sessionId);
    }
  }, [sessionId, currentChatId]);

  const currentChat = chats.find((c) => c.id === currentChatId);

  // Detect browser-initiated screen share stop (track ended)
  const prevScreenShareActive = useRef(screenShare.active);
  useEffect(() => {
    if (prevScreenShareActive.current && !screenShare.active) {
      // Screen share just stopped (browser UI or track ended)
      send("video.modeSwitch", { mode: "camera" });
      stopVideoStream();
      toast("Screen sharing stopped");
    }
    prevScreenShareActive.current = screenShare.active;
  }, [screenShare.active, send, stopVideoStream]);

  const isRecordingRef = useRef(false);

  // Voice streaming state
  const [isVoiceStreaming, setIsVoiceStreaming] = useState(false);
  const audioStreamRef = useRef<MediaStream | null>(null);

  const startVoice = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
      audioStreamRef.current = stream;
      await startVoiceInput(stream);
      setIsVoiceStreaming(true);
    } catch (err) {
      console.error("Failed to start voice:", err);
      toast.error("Microphone not available");
    }
  }, [startVoiceInput]);

  const stopVoice = useCallback(() => {
    stopVoiceInput();
    if (audioStreamRef.current) {
      audioStreamRef.current.getTracks().forEach((t) => t.stop());
      audioStreamRef.current = null;
    }
    setIsVoiceStreaming(false);
  }, [stopVoiceInput]);

  const handleToggleVoice = useCallback(async () => {
    if (isVoiceStreaming) {
      stopVoice();
    } else {
      await startVoice();
    }
  }, [isVoiceStreaming, startVoice, stopVoice]);

  // Auto-start video streaming when camera or screen share is active
  // Always stop first so the interval gets a fresh captureFrame closure
  useEffect(() => {
    stopVideoStream();
    if (isConnected && (camera.active || screenShare.active)) {
      startVideoStream(() => {
        if (screenShare.active) return screenShare.captureFrame();
        return camera.capturePhoto();
      });
    }
  }, [camera.active, screenShare.active, isConnected, startVideoStream, stopVideoStream, camera, screenShare]);

  // Auto-start voice streaming when camera or screen share becomes active
  useEffect(() => {
    const anyVideoActive = camera.active || screenShare.active;
    if (anyVideoActive && isConnected && !isVoiceStreaming) {
      startVoice();
    }
    if (!anyVideoActive && isVoiceStreaming) {
      stopVoice();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [camera.active, screenShare.active, isConnected]);

  // Handlers
  const handleRenameChat = useCallback(
    (newTitle: string) => {
      setChats((prev) =>
        prev.map((c) => (c.id === currentChatId ? { ...c, title: newTitle } : c))
      );
    },
    [currentChatId]
  );

  const handleToggleFavorite = useCallback(() => {
    setChats((prev) =>
      prev.map((c) =>
        c.id === currentChatId ? { ...c, favorite: !c.favorite } : c
      )
    );
  }, [currentChatId]);


  const handleSendMessage = useCallback(
    (text: string, attachments?: { id: string; name: string; type: "image" | "file"; preview?: string }[]) => {
      // Convert attachments to the format expected by useChat
      const formattedAttachments = attachments?.map((a) => ({
        type: a.type,
        data: a.preview || "",
      }));

      sendMessage(text, formattedAttachments);

      // Update chat title if first message
      if (messages.length === 0 && text.length > 0) {
        const title = text.length > 40 ? text.substring(0, 40) + "..." : text;
        handleRenameChat(title);
      }
    },
    [sendMessage, messages.length, handleRenameChat]
  );

  const handleCapturePhoto = useCallback((): string | null => {
    const photo = camera.capturePhoto();
    if (photo) {
      sendPhotoToAI(photo, "What do you see in this image?");
    }
    return photo;
  }, [camera, sendPhotoToAI]);

  const handleToggleSpeaker = useCallback(() => {
    setSpeakerOn((prev) => {
      toast(prev ? "Speaker off" : "Speaker on");
      return !prev;
    });
  }, []);

  const handleScreenShare = useCallback(async () => {
    if (screenShare.active) {
      // Stop — the useEffect above handles mode switch + toast
      screenShare.stopScreenShare();
    } else {
      // Stop camera before screen share — single source at a time
      if (camera.active) {
        camera.stopStream();
      }
      const started = await screenShare.startScreenShare();
      if (started) {
        send("video.modeSwitch", { mode: "screen" });
        toast("Sharing your screen");
      }
    }
  }, [screenShare, camera, send]);

  const handleOnboardingComplete = useCallback(() => {
    localStorage.setItem(ONBOARDING_KEY, "true");
    setShowOnboarding(false);
  }, []);

  const handleRequestMic = useCallback(async (): Promise<boolean> => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((t) => t.stop());
      return true;
    } catch {
      return false;
    }
  }, []);

  const handleRequestCamera = useCallback(async (): Promise<boolean> => {
    try {
      await camera.startCamera();
      return true;
    } catch {
      return false;
    }
  }, [camera]);

  const handleNewChat = useCallback(() => {
    clearChat();
    const newId = `chat-${Date.now()}`;
    const newChat: ChatSummary = {
      id: newId,
      title: "New conversation",
      status: "active",
      createdAt: new Date(),
      favorite: false,
    };
    setChats((prev) => [newChat, ...prev]);
    setCurrentChatId(newId);
  }, [clearChat]);

  const handleSelectChat = useCallback(
    (id: string) => {
      setCurrentChatId(id);
      // Note: In a full implementation, we'd load messages from storage/backend
      // Don't call clearChat() here - that resets the backend session
    },
    []
  );

  // Show loading state until hydrated
  if (!isHydrated) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  // Show onboarding overlay
  if (showOnboarding) {
    return (
      <OnboardingOverlay
        onComplete={handleOnboardingComplete}
        onRequestMic={handleRequestMic}
        onRequestCamera={handleRequestCamera}
      />
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Connection status indicator */}
      {!isConnected && (
        <div className="fixed top-2 left-1/2 -translate-x-1/2 z-50 flex items-center gap-2 rounded-full bg-destructive/90 px-3 py-1.5 text-xs font-medium text-destructive-foreground backdrop-blur-sm">
          <WifiOff className="h-3.5 w-3.5" />
          {connectionState === "connecting"
            ? "Connecting..."
            : connectionState === "reconnecting"
            ? "Reconnecting..."
            : "Disconnected"}
        </div>
      )}

      {/* Sidebar */}
      <ChatSidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onOpen={() => setSidebarOpen(true)}
        chats={chats}
        currentChatId={currentChatId}
        isMobile={isMobile}
        onNewChat={handleNewChat}
        onSelectChat={handleSelectChat}
        onSearchClick={() => setSearchOpen(true)}
      />

      <SearchOverlay
        isOpen={searchOpen}
        onClose={() => setSearchOpen(false)}
        chats={chats}
        onSelectChat={handleSelectChat}
        onNewChat={handleNewChat}
      />

      {/* Main content */}
      <div className="flex flex-1 min-h-0 min-w-0 flex-col relative">
        <div className="flex flex-1 min-h-0 flex-col">
          <div className="relative flex flex-col flex-1 min-h-0 overflow-hidden">
            {/* Screen share stop button */}
            {!sidebarOpen && screenShare.active && (
              <div className="pointer-events-none absolute left-0 right-0 top-0 z-30 flex items-center gap-2 p-4">
                <button
                  onClick={handleScreenShare}
                  className="pointer-events-auto flex items-center gap-1.5 rounded-xl bg-destructive/90 px-3 py-2 text-xs font-medium text-destructive-foreground backdrop-blur-sm transition-all duration-200 hover:bg-destructive active:scale-95"
                >
                  <MonitorOff className="h-3.5 w-3.5" />
                  Stop sharing
                </button>
              </div>
            )}

            <ChatHeader
              sidebarOpen={sidebarOpen}
              onToggleSidebar={() => setSidebarOpen(true)}
              chatTitle={currentChat?.title}
              isFavorite={currentChat?.favorite}
              onRename={handleRenameChat}
              onToggleFavorite={handleToggleFavorite}
            />

            <LargePreview>
              {(() => {
                const hasTask = isTaskActive && chatTaskSteps.length > 0;
                const hasReport = isReportActive && reportData !== null;
                const hasSidePanel = hasTask || hasReport;
                // When both panels active, each gets 50% of the side panel
                const bothActive = hasTask && hasReport;

                return (
                  <div className={cn(
                    "flex h-full",
                    hasSidePanel ? "flex-col md:flex-row" : "flex-col"
                  )}>
                    {/* Main content — 60% when side panel active */}
                    <div className={cn(
                      "flex flex-col overflow-hidden px-5",
                      hasSidePanel
                        ? "h-[60%] md:h-full md:w-[60%] md:border-r md:border-border/40"
                        : "h-full"
                    )}>
                      <div className="max-w-3xl sm:min-w-[400px] mx-auto w-full flex flex-col flex-1 min-h-0">
                        <div className="flex-1 min-h-0 overflow-hidden">
                          <ChatMessages
                            messages={messages.map((m) => ({
                              ...m,
                              type: m.type || "text",
                            }))}
                            thinkingSteps={thinkingSteps}
                            isThinking={isThinking}
                          />
                        </div>

                        <BottomBar
                          speakerOn={speakerOn}
                          cameraOn={camera.active}
                          onToggleSpeaker={handleToggleSpeaker}
                          onToggleCamera={() => {
                            if (camera.active) {
                              camera.stopStream();
                            } else {
                              if (screenShare.active) {
                                screenShare.stopScreenShare();
                              }
                              camera.startCamera();
                            }
                          }}
                          onSendMessage={handleSendMessage}
                          onCapturePhoto={handleCapturePhoto}
                          onScreenShare={handleScreenShare}
                          isScreenSharing={screenShare.active}
                          isVoiceStreaming={isVoiceStreaming}
                          onToggleVoice={handleToggleVoice}
                        />
                      </div>
                    </div>

                    {/* Side panels — 40% total, split 50/50 if both active */}
                    {hasSidePanel && (
                      <div className={cn(
                        "flex flex-col overflow-hidden",
                        "h-[40%] md:h-full md:w-[40%]",
                        "animate-in slide-in-from-bottom md:slide-in-from-right duration-300"
                      )}>
                        {/* Task panel */}
                        {hasTask && (
                          <div className={cn(
                            "overflow-y-auto p-4",
                            bothActive ? "h-1/2 border-b border-border/40" : "h-full"
                          )}>
                            <TaskProgressCard
                              steps={chatTaskSteps}
                              title={chatTaskTitle}
                              onToggleStep={chatHandleToggleStep}
                              onDismiss={dismissTask}
                            />
                          </div>
                        )}

                        {/* Report panel */}
                        {hasReport && (
                          <div className={cn(
                            "overflow-hidden",
                            bothActive ? "h-1/2" : "h-full"
                          )}>
                            <ReportPanel
                              report={reportData}
                              onDismiss={dismissReport}
                            />
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })()}
            </LargePreview>
          </div>
        </div>

        {/* Floating PiP - camera or screen share */}
        <FloatingPiP
          isTaskMode={isTaskActive}
          isCameraActive={camera.active || screenShare.active}
          sidebarOpen={sidebarOpen && !isMobile}
        >
          <CameraPreview
            compact
            camera={camera}
            screenShareStream={screenShare.active ? screenShare.stream : undefined}
            onToggle={() => {
              if (screenShare.active) return; // Don't toggle camera while screen sharing
              if (camera.active) camera.stopStream();
              else camera.startCamera();
            }}
          />
        </FloatingPiP>

      </div>
    </div>
  );
};

export default AppPageClient;
