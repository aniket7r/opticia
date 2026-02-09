"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useWebSocket } from "@/providers/WebSocketProvider";
import { WSMessage } from "@/lib/websocket";
import { AudioProcessor, AudioPlayer } from "@/lib/audio";
import type { Step } from "@/components/task/types";

export interface ReportData {
  reportId: string;
  topic: string;
  markdownContent?: string;
  htmlContent?: string;
  status: "generating" | "ready" | "error";
  error?: string;
  estimatedSeconds?: number;
}

export interface Message {
  id: string;
  role: "user" | "ai" | "system";
  content: string;
  timestamp: Date;
  type?: "text" | "thinking" | "task-summary";
  isStreaming?: boolean;
}

export interface ThinkingStep {
  icon: string;
  text: string;
  status: "pending" | "active" | "complete";
  timestamp?: string;
}

interface UseChatOptions {
  onToolCall?: (name: string, args: Record<string, unknown>) => void;
  onError?: (error: { code: string; message: string }) => void;
  captureFrame?: () => string | null;
}

export function useChat(options: UseChatOptions = {}) {
  const {
    isConnected,
    connectionState,
    sessionId,
    subscribe,
    sendText,
    sendAudioChunk,
    sendVideoFrame,
    sendPhoto,
    startNewConversation,
    send,
  } = useWebSocket();

  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [thinkingSteps, setThinkingSteps] = useState<ThinkingStep[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const [taskTitle, setTaskTitle] = useState("");
  const [taskSteps, setTaskSteps] = useState<Step[]>([]);
  const [isTaskActive, setIsTaskActive] = useState(false);
  const [reportData, setReportData] = useState<ReportData | null>(null);
  const [isReportActive, setIsReportActive] = useState(false);

  const audioProcessorRef = useRef<AudioProcessor | null>(null);
  const audioPlayerRef = useRef<AudioPlayer | null>(null);
  const isAiStreamingRef = useRef(false);
  const aiTextBufferRef = useRef("");
  const videoIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Initialize audio player
  useEffect(() => {
    audioPlayerRef.current = new AudioPlayer();
    return () => {
      audioPlayerRef.current?.dispose();
    };
  }, []);

  // Subscribe to AI responses
  useEffect(() => {
    const unsubscribeText = subscribe("ai.text", (msg: WSMessage) => {
      let { content, complete } = msg.payload as { content: string; complete?: boolean };

      // Strip task/report control patterns from displayed text
      content = content
        .replace(/\[TASK:\s*\{[^}]*\}\]/gi, "")
        .replace(/\[TASK_UPDATE:\s*\{.*?\}\]/gi, "")
        .replace(/\[TASK_COMPLETE\]/gi, "")
        .replace(/\[REPORT:\s*[^\]]*\]/gi, "");

      // Skip empty content after stripping
      if (!content && !complete) return;

      // Track AI streaming state for thinking steps
      if (!isAiStreamingRef.current) {
        isAiStreamingRef.current = true;
        aiTextBufferRef.current = "";
        setThinkingSteps([]);
        setIsThinking(true);
      }

      aiTextBufferRef.current += content;

      // Parse bold headers (on their own line, optionally as markdown headings) as thinking steps
      const headerPattern = /(?:^|\n)\s*(?:#{1,6}\s+)?\*\*([^*\n]+)\*\*/g;
      const headers: string[] = [];
      let match;
      while ((match = headerPattern.exec(aiTextBufferRef.current)) !== null) {
        headers.push(match[1].trim());
      }

      if (headers.length > 0) {
        const icons = ["🔍", "💭", "🔎", "💡", "📝", "✨"];
        setThinkingSteps(
          headers.map((text, i) => ({
            icon: icons[i % icons.length],
            text,
            status: (complete || i < headers.length - 1) ? "complete" as const : "active" as const,
          }))
        );
      }

      setMessages((prev) => {
        // Finalize any streaming user transcription before adding AI text
        const updated = prev.map((m) =>
          m.role === "user" && m.isStreaming ? { ...m, isStreaming: false } : m
        );

        // Find or create AI message
        const lastMessage = updated[updated.length - 1];

        if (lastMessage?.role === "ai" && lastMessage.isStreaming) {
          // Append to existing streaming message
          return updated.map((m, i) =>
            i === updated.length - 1
              ? { ...m, content: m.content + content, isStreaming: !complete }
              : m
          );
        } else {
          // Create new AI message
          const newMessage: Message = {
            id: crypto.randomUUID(),
            role: "ai",
            content,
            timestamp: new Date(),
            isStreaming: !complete,
          };
          return [...updated, newMessage];
        }
      });

      if (complete) {
        isAiStreamingRef.current = false;
        setIsLoading(false);
        setIsThinking(false);
      }
    });

    const unsubscribeAudio = subscribe("ai.audio", (msg: WSMessage) => {
      const { data, sampleRate } = msg.payload as { data: string; sampleRate: number };
      audioPlayerRef.current?.enqueue(data, sampleRate);
    });

    const unsubscribeUserTranscription = subscribe("user.transcription", (msg: WSMessage) => {
      const { content } = msg.payload as { content: string };
      if (!content) return;

      setMessages((prev) => {
        const lastMessage = prev[prev.length - 1];

        if (lastMessage?.role === "user" && lastMessage.isStreaming) {
          // Append to existing streaming user transcription
          return prev.map((m, i) =>
            i === prev.length - 1
              ? { ...m, content: m.content + content }
              : m
          );
        } else {
          // Create new user message from voice transcription
          const newMessage: Message = {
            id: crypto.randomUUID(),
            role: "user",
            content,
            timestamp: new Date(),
            isStreaming: true,
          };
          return [...prev, newMessage];
        }
      });
    });

    const unsubscribeToolCall = subscribe("ai.tool_call", (msg: WSMessage) => {
      const { name, args } = msg.payload as { name: string; args: Record<string, unknown> };
      options.onToolCall?.(name, args);

      // Add thinking step for tool call
      setThinkingSteps((prev) => [
        ...prev,
        {
          icon: "🔧",
          text: `Using ${name}...`,
          status: "active",
          timestamp: new Date().toISOString(),
        },
      ]);
    });

    const unsubscribeTurnComplete = subscribe("ai.turn_complete", () => {
      isAiStreamingRef.current = false;
      setIsLoading(false);
      setIsThinking(false);
      // Mark all thinking steps as complete
      setThinkingSteps((prev) =>
        prev.map((s) => ({ ...s, status: "complete" as const }))
      );
      // Finalize any streaming AI message and strip task patterns from accumulated content
      setMessages((prev) =>
        prev.map((m, i) => {
          if (i === prev.length - 1 && m.role === "ai" && m.isStreaming) {
            let cleaned = m.content;
            // Strip [TASK: {...}] using bracket counting (handles nested JSON)
            const taskIdx = cleaned.toUpperCase().indexOf("[TASK:");
            if (taskIdx !== -1) {
              const braceStart = cleaned.indexOf("{", taskIdx);
              if (braceStart !== -1) {
                let depth = 0;
                for (let j = braceStart; j < cleaned.length; j++) {
                  if (cleaned[j] === "{") depth++;
                  else if (cleaned[j] === "}") {
                    depth--;
                    if (depth === 0) {
                      const closeBracket = cleaned.indexOf("]", j);
                      if (closeBracket !== -1) {
                        cleaned = cleaned.substring(0, taskIdx) + cleaned.substring(closeBracket + 1);
                      }
                      break;
                    }
                  }
                }
              }
            }
            cleaned = cleaned
              .replace(/\[TASK_UPDATE:\s*\{[^}]*\}\]/gi, "")
              .replace(/\[TASK_COMPLETE\]/gi, "")
              .replace(/\[REPORT:\s*[^\]]*\]/gi, "")
              .trim();
            return { ...m, content: cleaned, isStreaming: false };
          }
          return m;
        })
      );
    });

    const unsubscribeError = subscribe("error", (msg: WSMessage) => {
      const error = msg.payload as { code: string; message: string };
      options.onError?.(error);
      setIsLoading(false);
    });

    const unsubscribeTaskStart = subscribe("task.start", (msg: WSMessage) => {
      const { title, steps } = msg.payload as { title: string; steps: Step[] };
      setTaskTitle(title);
      setTaskSteps(steps);
      setIsTaskActive(true);
    });

    const unsubscribeTaskUpdate = subscribe("task.step_update", (msg: WSMessage) => {
      const { stepIndex, status } = msg.payload as { stepIndex: number; status: string };
      setTaskSteps((prev) =>
        prev.map((s, i) => {
          if (i === stepIndex) {
            return { ...s, status: status as Step["status"] };
          }
          // Advance "current" marker to next incomplete step
          if (i === stepIndex + 1 && s.status === "upcoming") {
            return { ...s, status: "current" };
          }
          return s;
        })
      );
    });

    const unsubscribeTaskComplete = subscribe("task.complete", () => {
      setTaskSteps((prev) => prev.map((s) => ({ ...s, status: "completed" as const })));
      setTimeout(() => {
        setIsTaskActive(false);
        setTaskSteps([]);
        setTaskTitle("");
      }, 2000);
    });

    // Report event subscriptions
    const unsubscribeReportGenerating = subscribe("report.generating", (msg: WSMessage) => {
      const { reportId, topic, estimatedSeconds } = msg.payload as {
        reportId: string; topic: string; estimatedSeconds: number;
      };
      setReportData({
        reportId,
        topic,
        status: "generating",
        estimatedSeconds,
      });
      setIsReportActive(true);
    });

    const unsubscribeReportReady = subscribe("report.ready", (msg: WSMessage) => {
      const { reportId, topic, markdownContent, htmlContent } = msg.payload as {
        reportId: string; topic: string; markdownContent: string; htmlContent: string;
      };
      setReportData({
        reportId,
        topic,
        markdownContent,
        htmlContent,
        status: "ready",
      });
    });

    const unsubscribeReportError = subscribe("report.error", (msg: WSMessage) => {
      const { reportId, error } = msg.payload as { reportId: string; error: string; retryable: boolean };
      setReportData((prev) =>
        prev ? { ...prev, status: "error", error } : null
      );
    });

    const unsubscribeReset = subscribe("conversation.reset", () => {
      setMessages([]);
      setThinkingSteps([]);
      setIsThinking(false);
      setTaskSteps([]);
      setTaskTitle("");
      setIsTaskActive(false);
      setReportData(null);
      setIsReportActive(false);
    });

    return () => {
      unsubscribeText();
      unsubscribeAudio();
      unsubscribeUserTranscription();
      unsubscribeToolCall();
      unsubscribeTurnComplete();
      unsubscribeError();
      unsubscribeTaskStart();
      unsubscribeTaskUpdate();
      unsubscribeTaskComplete();
      unsubscribeReportGenerating();
      unsubscribeReportReady();
      unsubscribeReportError();
      unsubscribeReset();
    };
  }, [subscribe, options]);

  // Send text message
  const sendMessage = useCallback(
    (content: string, attachments?: { type: string; data: string }[]) => {
      if (!content.trim() && !attachments?.length) return;

      // Add user message
      const userMessage: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);
      setThinkingSteps([]);
      setIsThinking(false);
      isAiStreamingRef.current = false;

      // Send attachments as photos if present
      if (attachments?.length) {
        attachments.forEach((att) => {
          if (att.type === "image") {
            sendPhoto(att.data, content);
          }
        });
      } else {
        // If camera is active, capture the current frame to send inline with text
        let frameBase64: string | undefined;
        if (options.captureFrame) {
          const dataUrl = options.captureFrame();
          if (dataUrl) {
            frameBase64 = dataUrl.startsWith("data:") ? dataUrl.split(",")[1] : dataUrl;
          }
        }
        sendText(content, frameBase64);
      }
    },
    [sendText, sendPhoto]
  );

  // Start video streaming (1 FPS)
  const startVideoStream = useCallback(
    (captureFrame: () => string | null) => {
      if (videoIntervalRef.current) return;

      videoIntervalRef.current = setInterval(() => {
        const frame = captureFrame();
        if (frame) {
          sendVideoFrame(frame);
        }
      }, 1000); // 1 FPS
    },
    [sendVideoFrame]
  );

  // Stop video streaming
  const stopVideoStream = useCallback(() => {
    if (videoIntervalRef.current) {
      clearInterval(videoIntervalRef.current);
      videoIntervalRef.current = null;
    }
  }, []);

  // Start voice input
  const startVoiceInput = useCallback(
    async (stream: MediaStream) => {
      audioProcessorRef.current = new AudioProcessor();
      await audioProcessorRef.current.start(stream, (base64Pcm) => {
        sendAudioChunk(base64Pcm);
      });
    },
    [sendAudioChunk]
  );

  // Stop voice input
  const stopVoiceInput = useCallback(() => {
    audioProcessorRef.current?.stop();
    audioProcessorRef.current = null;
  }, []);

  // Capture and send photo
  const capturePhoto = useCallback(
    (dataUrl: string, context?: string) => {
      sendPhoto(dataUrl, context);

      // Add user message for photo
      const userMessage: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content: context || "📷 Photo captured",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);
    },
    [sendPhoto]
  );

  // Clear chat
  const clearChat = useCallback(() => {
    startNewConversation();
    setMessages([]);
    setThinkingSteps([]);
    setTaskSteps([]);
    setTaskTitle("");
    setIsTaskActive(false);
  }, [startNewConversation]);

  // Task step toggle (user clicks checkbox) — also notifies AI
  const taskStepsRef = useRef<Step[]>([]);
  taskStepsRef.current = taskSteps;

  const handleToggleStep = useCallback((stepId: string) => {
    const prev = taskStepsRef.current;
    const stepIndex = prev.findIndex((s) => s.id === stepId);
    if (stepIndex === -1) return;
    const step = prev[stepIndex];
    const newStatus = step.status === "completed" ? "upcoming" : "completed";

    // Update state
    setTaskSteps(
      prev.map((s, i) => {
        if (i === stepIndex) return { ...s, status: newStatus as Step["status"] };
        if (newStatus === "completed" && i === stepIndex + 1 && s.status === "upcoming") {
          return { ...s, status: "current" as const };
        }
        return s;
      })
    );

    // Notify backend (once, outside updater)
    if (newStatus === "completed") {
      send("task.step_done", { stepIndex, stepId });
    }
  }, [send]);

  // Dismiss task
  const dismissTask = useCallback(() => {
    setIsTaskActive(false);
    setTaskSteps([]);
    setTaskTitle("");
  }, []);

  // Dismiss report
  const dismissReport = useCallback(() => {
    setIsReportActive(false);
    setReportData(null);
  }, []);

  // Stop audio playback
  const stopAudioPlayback = useCallback(() => {
    audioPlayerRef.current?.stop();
  }, []);

  return {
    // State
    messages,
    isLoading,
    isConnected,
    connectionState,
    sessionId,
    thinkingSteps,
    isThinking,
    taskTitle,
    taskSteps,
    isTaskActive,
    reportData,
    isReportActive,

    // Actions
    sendMessage,
    startVoiceInput,
    stopVoiceInput,
    startVideoStream,
    stopVideoStream,
    capturePhoto,
    clearChat,
    stopAudioPlayback,
    handleToggleStep,
    dismissTask,
    dismissReport,

    // Low-level access
    send,
  };
}
