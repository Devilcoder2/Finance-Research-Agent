import { API_ENDPOINTS, STORAGE_KEYS } from '../constants';

export interface SectionAnnotation {
  section_id: string;
  comment: string;
}

export interface BriefEvaluation {
  score_factual: number;
  score_clarity: number;
  score_coverage: number;
  rubric_justification: string;
}

export interface BriefItem {
  id: string;
  ticker: string;
  brief_content: {
    executive_summary: string;
    business_overview: string;
    financial_analysis: string;
    risk_factors: string;
    verdict: string;
  };
  revision_count: number;
  created_at: string;
  evaluations: BriefEvaluation[];
  annotations: {
    section_id: string;
    comment: string;
    created_at: string;
  }[];
}

export interface ThreadItem {
  thread_id: string;
  name: string;
  tickers: string[];
  status: 'initiated' | 'paused' | 'completed' | 'failed' | 'revision';
  created_at: string;
}

export interface AnalyticsDetails {
  id: string;
  thread_id: string;
  thread_name: string;
  prompt_tokens: number;
  completion_tokens: number;
  estimated_cost_usd: number;
  latency_seconds: number;
  created_at: string;
}

export interface AnalyticsResponse {
  summary: {
    total_runs: number;
    total_cost_usd: number;
    total_prompt_tokens: number;
    total_completion_tokens: number;
    average_latency_seconds: number;
  };
  details: AnalyticsDetails[];
}

/**
 * Builds request headers dynamically injecting Bearer token if present in localStorage.
 */
const getHeaders = (): Record<string, string> => {
  const token = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
};

export const api = {
  /**
   * Performs user registration.
   */
  async signup(email: string, password: string): Promise<{ id: string; email: string; created_at: string }> {
    const response = await fetch(API_ENDPOINTS.SIGNUP, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || `Registration failed: ${response.statusText}`);
    }

    return response.json();
  },

  /**
   * Performs user login.
   */
  async login(email: string, password: string): Promise<{ access_token: string; token_type: string }> {
    const response = await fetch(API_ENDPOINTS.LOGIN, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || `Login failed: ${response.statusText}`);
    }

    return response.json();
  },

  /**
   * Starts a new research thread for a list of tickers.
   */
  async startResearch(tickers: string[], name?: string): Promise<{ thread_id: string; status: string }> {
    const response = await fetch(API_ENDPOINTS.START_RESEARCH, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ tickers, name }),
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || `Failed to start research: ${response.statusText}`);
    }

    return response.json();
  },

  /**
   * Resumes a research thread at an interrupt point (approval / rejection feedback loop).
   */
  async resumeResearch(
    threadId: string,
    ticker: string,
    action: 'approve' | 'reject',
    feedback: SectionAnnotation[] = []
  ): Promise<{ status: string; message: string }> {
    const response = await fetch(API_ENDPOINTS.RESUME_RESEARCH, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({
        thread_id: threadId,
        ticker,
        action,
        feedback,
      }),
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || `Failed to resume research: ${response.statusText}`);
    }

    return response.json();
  },

  /**
   * Fetches list of all threads.
   */
  async getThreads(): Promise<ThreadItem[]> {
    const response = await fetch(API_ENDPOINTS.GET_THREADS, {
      headers: getHeaders(),
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || `Failed to fetch threads: ${response.statusText}`);
    }

    return response.json();
  },

  /**
   * Fetches all investment briefs associated with a thread ID.
   */
  async getBriefs(threadId: string): Promise<BriefItem[]> {
    const response = await fetch(API_ENDPOINTS.GET_BRIEFS(threadId), {
      headers: getHeaders(),
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || `Failed to fetch briefs: ${response.statusText}`);
    }

    return response.json();
  },

  /**
   * Fetches cost and performance analytics.
   */
  async getAnalytics(): Promise<AnalyticsResponse> {
    const response = await fetch(API_ENDPOINTS.GET_ANALYTICS, {
      headers: getHeaders(),
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || `Failed to fetch analytics: ${response.statusText}`);
    }

    return response.json();
  },
};
