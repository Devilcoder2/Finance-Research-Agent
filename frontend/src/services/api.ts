import { API_ENDPOINTS } from '../constants';

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

export const api = {
  /**
   * Starts a new research thread for a list of tickers.
   */
  async startResearch(tickers: string[]): Promise<{ thread_id: string; status: string }> {
    const response = await fetch(API_ENDPOINTS.START_RESEARCH, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ tickers }),
    });

    if (!response.ok) {
      throw new Error(`Failed to start research: ${response.statusText}`);
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
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        thread_id: threadId,
        ticker,
        action,
        feedback,
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to resume research: ${response.statusText}`);
    }

    return response.json();
  },

  /**
   * Fetches list of all threads.
   */
  async getThreads(): Promise<ThreadItem[]> {
    const response = await fetch(API_ENDPOINTS.GET_THREADS);

    if (!response.ok) {
      throw new Error(`Failed to fetch threads: ${response.statusText}`);
    }

    return response.json();
  },

  /**
   * Fetches all investment briefs associated with a thread ID.
   */
  async getBriefs(threadId: string): Promise<BriefItem[]> {
    const response = await fetch(API_ENDPOINTS.GET_BRIEFS(threadId));

    if (!response.ok) {
      throw new Error(`Failed to fetch briefs: ${response.statusText}`);
    }

    return response.json();
  },
};
