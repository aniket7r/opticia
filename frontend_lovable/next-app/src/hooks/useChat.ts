"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useWebSocket } from "@/providers/WebSocketProvider";
import { WSMessage } from "@/lib/websocket";
import { AudioProcessor, AudioPlayer } from "@/lib/audio";

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

  const audioProcessorRef = useRef<AudioProcessor | null>(null);
  const audioPlayerRef = useRef<AudioPlayer | null>(null);
  const currentAiMessageRef = useRef<string | null>(null);
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
      const { content, complete } = msg.payload as { content: string; complete?: boolean };

      setMessages((prev) => {
        // Find or create AI message
        const lastMessage = prev[prev.length - 1];

        if (lastMessage?.role === "ai" && lastMessage.isStreaming) {
          // Append to existing streaming message
          return prev.map((m, i) =>
            i === prev.length - 1
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
          return [...prev, newMessage];
        }
      });

      if (complete) {
        setIsLoading(false);
        setIsThinking(false);
      }
    });

    const unsubscribeAudio = subscribe("ai.audio", (msg: WSMessage) => {
      const { data, sampleRate } = msg.payload as { data: string; sampleRate: number };
      audioPlayerRef.current?.enqueue(data, sampleRate);
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

    const unsubscribeError = subscribe("error", (msg: WSMessage) => {
      const error = msg.payload as { code: string; message: string };
      options.onError?.(error);
      setIsLoading(false);
    });

    const unsubscribeReset = subscribe("conversation.reset", () => {
      setMessages([]);
      setThinkingSteps([]);
      setIsThinking(false);
    });

    return () => {
      unsubscribeText();
      unsubscribeAudio();
      unsubscribeToolCall();
      unsubscribeError();
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

      // Send attachments as photos if present
      if (attachments?.length) {
        attachments.forEach((att) => {
          if (att.type === "image") {
            sendPhoto(att.data, content);
          }
        });
      } else {
        sendText(content);
      }
    },
    [sendText, sendPhoto]
  );

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
  }, [startNewConversation]);

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

    // Actions
    sendMessage,
    startVoiceInput,
    stopVoiceInput,
    startVideoStream,
    stopVideoStream,
    capturePhoto,
    clearChat,
    stopAudioPlayback,

    // Low-level access
    send,
  };
}
