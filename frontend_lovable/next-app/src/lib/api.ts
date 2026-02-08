/**
 * REST API client for Opticia AI backend.
 */

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface FetchOptions extends RequestInit {
  params?: Record<string, string | number>;
}

async function fetchApi<T>(
  endpoint: string,
  options: FetchOptions = {}
): Promise<T> {
  const { params, ...fetchOptions } = options;

  let url = `${API_BASE_URL}${endpoint}`;

  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      searchParams.append(key, String(value));
    });
    url += `?${searchParams.toString()}`;
  }

  const response = await fetch(url, {
    ...fetchOptions,
    headers: {
      "Content-Type": "application/json",
      ...fetchOptions.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.message || `API Error: ${response.status}`);
  }

  return response.json();
}

// ============================================================================
// Admin API
// ============================================================================

export interface DashboardStats {
  active_sessions: number;
  total_sessions_today: number;
  total_tokens_today: number;
  total_cost_today: number;
  cache_hit_rate: number;
  avg_session_duration: number;
  fallback_count_today: number;
  error_count_today: number;
  tool_usage: Record<string, number>;
}

export interface Session {
  id: string;
  created_at: string;
  ended_at: string | null;
  status: string;
  tool_calls_count: number;
  fallback_activations: number;
  total_tokens: number;
}

export interface DailyCost {
  date: string;
  cost: number;
}

export const adminApi = {
  /**
   * Get dashboard statistics.
   */
  async getStats(): Promise<DashboardStats> {
    return fetchApi<DashboardStats>("/admin/stats");
  },

  /**
   * Get recent sessions.
   */
  async getSessions(limit: number = 20): Promise<Session[]> {
    return fetchApi<Session[]>("/admin/sessions", {
      params: { limit },
    });
  },

  /**
   * Get daily cost breakdown.
   */
  async getCostsByDay(days: number = 7): Promise<DailyCost[]> {
    return fetchApi<DailyCost[]>("/admin/costs", {
      params: { days },
    });
  },

  /**
   * Health check.
   */
  async healthCheck(): Promise<{ status: string; active_connections: number }> {
    return fetchApi("/admin/health");
  },
};

// ============================================================================
// Health API
// ============================================================================

export const healthApi = {
  /**
   * Basic health check.
   */
  async check(): Promise<{ status: string }> {
    return fetchApi("/health");
  },
};

// ============================================================================
// Preferences API (alternative to WebSocket)
// ============================================================================

export interface UserPreferences {
  mode: "voice" | "text";
  proactivity_level: "minimal" | "balanced" | "proactive";
  auto_fallback: boolean;
  show_thinking: boolean;
  camera_position: string;
}

export const preferencesApi = {
  /**
   * Get preferences for a session.
   */
  async get(sessionId: string): Promise<UserPreferences> {
    return fetchApi<UserPreferences>(`/sessions/${sessionId}/preferences`);
  },

  /**
   * Update preferences for a session.
   */
  async update(
    sessionId: string,
    preferences: Partial<UserPreferences>
  ): Promise<UserPreferences> {
    return fetchApi<UserPreferences>(`/sessions/${sessionId}/preferences`, {
      method: "PUT",
      body: JSON.stringify(preferences),
    });
  },
};
