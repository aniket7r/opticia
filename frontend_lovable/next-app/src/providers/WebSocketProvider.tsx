"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  useRef,
  type ReactNode,
} from "react";
import {
  WebSocketClient,
  ConnectionState,
  MessageType,
  WSMessage,
  WSError,
  MessageHandler,
} from "@/lib/websocket";

interface WebSocketContextType {
  // Connection state
  isConnected: boolean;
  connectionState: ConnectionState;
  sessionId: string | null;
  error: WSError | null;

  // Actions
  connect: () => void;
  disconnect: () => void;
  send: <T = Record<string, unknown>>(type: MessageType, payload: T) => boolean;
  subscribe: (type: MessageType, handler: MessageHandler) => () => void;

  // Convenience methods
  sendText: (content: string) => void;
  sendAudioChunk: (data: string) => void;
  sendVideoFrame: (data: string) => void;
  sendPhoto: (data: string, context?: string) => void;
  startNewConversation: () => void;
}

const WebSocketContext = createContext<WebSocketContextType | null>(null);

interface WebSocketProviderProps {
  children: ReactNode;
  autoConnect?: boolean;
}

export function WebSocketProvider({
  children,
  autoConnect = true,
}: WebSocketProviderProps) {
  const [connectionState, setConnectionState] = useState<ConnectionState>("disconnected");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [error, setError] = useState<WSError | null>(null);
  const clientRef = useRef<WebSocketClient | null>(null);

  // Initialize WebSocket client (only on client side)
  useEffect(() => {
    // Skip on server side
    if (typeof window === "undefined") return;

    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws/session";

    clientRef.current = new WebSocketClient({
      url: wsUrl,
      onStateChange: (state) => {
        setConnectionState(state);
        if (state === "connected" && clientRef.current) {
          setSessionId(clientRef.current.sessionId);
        }
      },
      onError: (err) => {
        setError(err);
        console.warn("[WebSocket] Error:", err);
      },
      onMessage: (message) => {
        // Handle session ID updates
        if (message.type === "connection.established") {
          setSessionId(message.payload.sessionId as string);
        }
        // Clear error on successful message
        if (message.type !== "error") {
          setError(null);
        }
      },
    });

    if (autoConnect) {
      clientRef.current.connect();
    }

    return () => {
      clientRef.current?.disconnect();
    };
  }, [autoConnect]);

  const connect = useCallback(() => {
    clientRef.current?.connect();
  }, []);

  const disconnect = useCallback(() => {
    clientRef.current?.disconnect();
    setSessionId(null);
  }, []);

  const send = useCallback(<T = Record<string, unknown>>(
    type: MessageType,
    payload: T
  ): boolean => {
    return clientRef.current?.send(type, payload) ?? false;
  }, []);

  const subscribe = useCallback((type: MessageType, handler: MessageHandler): (() => void) => {
    return clientRef.current?.subscribe(type, handler) ?? (() => {});
  }, []);

  // Convenience methods
  const sendText = useCallback((content: string) => {
    send("text.send", { content });
  }, [send]);

  const sendAudioChunk = useCallback((data: string) => {
    send("audio.chunk", {
      data,
      format: "pcm16",
      sampleRate: 16000,
    });
  }, [send]);

  const sendVideoFrame = useCallback((data: string) => {
    // Extract base64 data from data URL if needed
    const base64Data = data.startsWith("data:") ? data.split(",")[1] : data;
    send("video.frame", {
      data: base64Data,
      mimeType: "image/jpeg",
    });
  }, [send]);

  const sendPhoto = useCallback((data: string, context?: string) => {
    const base64Data = data.startsWith("data:") ? data.split(",")[1] : data;
    send("photo.capture", {
      data: base64Data,
      mimeType: "image/jpeg",
      context,
    });
  }, [send]);

  const startNewConversation = useCallback(() => {
    send("conversation.new", {});
  }, [send]);

  const value: WebSocketContextType = {
    isConnected: connectionState === "connected",
    connectionState,
    sessionId,
    error,
    connect,
    disconnect,
    send,
    subscribe,
    sendText,
    sendAudioChunk,
    sendVideoFrame,
    sendPhoto,
    startNewConversation,
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
}

export function useWebSocket(): WebSocketContextType {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error("useWebSocket must be used within a WebSocketProvider");
  }
  return context;
}
