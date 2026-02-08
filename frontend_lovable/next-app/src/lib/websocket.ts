/**
 * WebSocket client for Opticia AI backend.
 * Handles connection, reconnection, and message protocol.
 */

export type MessageType =
  // Session
  | "session.start"
  | "session.end"
  | "session.ready"
  | "session.ended"
  | "session.reconnecting"
  | "session.reconnected"
  | "mode.switch"
  | "mode.switched"
  | "connection.established"
  // AI Communication
  | "text.send"
  | "ai.text"
  | "ai.audio"
  | "ai.tool_call"
  | "audio.chunk"
  | "thinking.show"
  | "thinking.enabled"
  // Vision
  | "video.frame"
  | "photo.capture"
  | "video.modeSwitch"
  | "video.modeSwitched"
  // Tools
  | "tool.execute"
  | "tool.result"
  | "tool.response"
  // Preferences
  | "preferences.get"
  | "preferences.loaded"
  | "preferences.update"
  | "preferences.updated"
  // Resilience
  | "fallback.trigger"
  | "fallback.activated"
  | "fallback.recover"
  | "fallback.recovered"
  | "network.ping"
  | "network.pong"
  | "network.degraded"
  | "network.stats"
  // Conversation
  | "conversation.new"
  | "conversation.reset"
  // Error
  | "error";

export interface WSMessage<T = Record<string, unknown>> {
  type: MessageType;
  sessionId?: string;
  timestamp?: string;
  payload: T;
}

export interface WSError {
  code: string;
  message: string;
  recoverable: boolean;
}

export type ConnectionState = "connecting" | "connected" | "disconnected" | "reconnecting";

export type MessageHandler = (message: WSMessage) => void;

interface WebSocketClientConfig {
  url: string;
  onStateChange?: (state: ConnectionState) => void;
  onMessage?: MessageHandler;
  onError?: (error: WSError) => void;
  reconnectAttempts?: number;
  reconnectDelay?: number;
}

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private config: Required<WebSocketClientConfig>;
  private reconnectCount = 0;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private pingInterval: NodeJS.Timeout | null = null;
  private messageQueue: WSMessage[] = [];
  private _sessionId: string | null = null;
  private _state: ConnectionState = "disconnected";
  private messageHandlers: Map<MessageType, Set<MessageHandler>> = new Map();

  constructor(config: WebSocketClientConfig) {
    this.config = {
      reconnectAttempts: 5,
      reconnectDelay: 1000,
      onStateChange: () => {},
      onMessage: () => {},
      onError: () => {},
      ...config,
    };
  }

  get sessionId(): string | null {
    return this._sessionId;
  }

  get state(): ConnectionState {
    return this._state;
  }

  get isConnected(): boolean {
    return this._state === "connected";
  }

  private setState(state: ConnectionState): void {
    this._state = state;
    this.config.onStateChange(state);
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    this.setState("connecting");

    try {
      this.ws = new WebSocket(this.config.url);
      this.setupEventHandlers();
    } catch (error) {
      console.error("[WS] Connection error:", error);
      this.handleReconnect();
    }
  }

  private setupEventHandlers(): void {
    if (!this.ws) return;

    this.ws.onopen = () => {
      console.log("[WS] Connected");
      this.reconnectCount = 0;
      this.startPingInterval();
    };

    this.ws.onmessage = (event) => {
      try {
        const message: WSMessage = JSON.parse(event.data);
        this.handleMessage(message);
      } catch (error) {
        console.error("[WS] Failed to parse message:", error);
      }
    };

    this.ws.onclose = (event) => {
      console.log("[WS] Disconnected:", event.code, event.reason);
      this.cleanup();

      if (event.code !== 1000) {
        // Abnormal close, attempt reconnect
        this.handleReconnect();
      } else {
        this.setState("disconnected");
      }
    };

    this.ws.onerror = (error) => {
      console.error("[WS] Error:", error);
    };
  }

  private handleMessage(message: WSMessage): void {
    // Handle connection established
    if (message.type === "connection.established") {
      this._sessionId = message.payload.sessionId as string;
      this.setState("connected");
      this.flushMessageQueue();

      // Auto-start session
      this.send("session.start", { mode: "voice" });
    }

    // Handle errors
    if (message.type === "error") {
      const error = message.payload as WSError;
      this.config.onError(error);
    }

    // Call registered handlers
    const handlers = this.messageHandlers.get(message.type);
    if (handlers) {
      handlers.forEach((handler) => handler(message));
    }

    // Call global handler
    this.config.onMessage(message);
  }

  private handleReconnect(): void {
    if (this.reconnectCount >= this.config.reconnectAttempts) {
      console.error("[WS] Max reconnect attempts reached");
      this.setState("disconnected");
      return;
    }

    this.setState("reconnecting");
    this.reconnectCount++;

    const delay = this.config.reconnectDelay * Math.pow(2, this.reconnectCount - 1);
    console.log(`[WS] Reconnecting in ${delay}ms (attempt ${this.reconnectCount})`);

    this.reconnectTimeout = setTimeout(() => {
      this.connect();
    }, delay);
  }

  private startPingInterval(): void {
    this.pingInterval = setInterval(() => {
      if (this.isConnected) {
        const start = Date.now();
        this.send("network.ping", {
          latencyMs: 0,
          timestamp: start
        });
      }
    }, 30000); // Ping every 30 seconds
  }

  private cleanup(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
  }

  private flushMessageQueue(): void {
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift();
      if (message) {
        this.sendRaw(message);
      }
    }
  }

  private sendRaw(message: WSMessage): boolean {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return false;
    }

    try {
      this.ws.send(JSON.stringify(message));
      return true;
    } catch (error) {
      console.error("[WS] Send error:", error);
      return false;
    }
  }

  send<T = Record<string, unknown>>(type: MessageType, payload: T): boolean {
    const message: WSMessage<T> = {
      type,
      payload,
    };

    if (!this.isConnected) {
      // Queue message for later
      this.messageQueue.push(message as WSMessage);
      return false;
    }

    return this.sendRaw(message as WSMessage);
  }

  subscribe(type: MessageType, handler: MessageHandler): () => void {
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, new Set());
    }
    this.messageHandlers.get(type)!.add(handler);

    // Return unsubscribe function
    return () => {
      this.messageHandlers.get(type)?.delete(handler);
    };
  }

  disconnect(): void {
    this.cleanup();

    if (this.ws) {
      this.send("session.end", {});
      this.ws.close(1000, "Client disconnect");
      this.ws = null;
    }

    this._sessionId = null;
    this.setState("disconnected");
  }
}

// Singleton instance
let wsClient: WebSocketClient | null = null;

export function getWebSocketClient(): WebSocketClient {
  if (!wsClient) {
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws/session";
    wsClient = new WebSocketClient({ url: wsUrl });
  }
  return wsClient;
}
