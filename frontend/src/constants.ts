// Application-wide Constants & Configurations

// API Base URL (usually proxy-routed or pointed directly to backend)
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// API Endpoints
export const API_ENDPOINTS = {
  LOGIN: `${API_BASE_URL}/api/auth/login`,
  SIGNUP: `${API_BASE_URL}/api/auth/signup`,
  START_RESEARCH: `${API_BASE_URL}/api/research/start`,
  RESUME_RESEARCH: `${API_BASE_URL}/api/research/resume`,
  GET_THREADS: `${API_BASE_URL}/api/research/threads`,
  GET_BRIEFS: (threadId: string) => `${API_BASE_URL}/api/research/briefs/${threadId}`,
  STREAM_RESEARCH: (threadId: string) => `${API_BASE_URL}/api/research/stream/${threadId}`,
  GET_ANALYTICS: `${API_BASE_URL}/api/research/analytics`,
};

// Default Authentication configuration
export const DEFAULT_USER = {
  id: '00000000-0000-0000-0000-000000000000',
  email: 'analyst@example.com',
  name: 'Senior Financial Analyst',
};

// UI Theme Custom Styling Constants (for CSS mappings)
export const THEME = {
  PRIMARY_COLOR: 'var(--primary-glow)',
  BG_GLASS: 'var(--bg-glass)',
  BORDER_GLASS: 'var(--border-glass)',
  TEXT_BRIGHT: 'var(--text-bright)',
  TEXT_MUTED: 'var(--text-muted)',
};

// LangGraph Agent Node Names mapping to user-friendly titles, descriptions and colors
export interface NodeInfo {
  label: string;
  description: string;
  color: string; // Tailwind/CSS color scheme mapping class or value
}

export const AGENT_NODES: Record<string, NodeInfo> = {
  load_memories: {
    label: 'Semantic Memory Loader',
    description: 'Retrieving historical research briefs and analyst preferences via pgvector.',
    color: '#a855f7', // Purple
  },
  run_scraper: {
    label: 'Web Scraper Worker',
    description: 'Harvesting SEC filings (10-K/10-Q), earnings call transcripts, and news via Tavily/SEC EDGAR.',
    color: '#3b82f6', // Blue
  },
  run_quant: {
    label: 'Quantitative Metrics Engine',
    description: 'Fetching price history, balance sheets, and key ratios via yfinance API.',
    color: '#06b6d4', // Cyan
  },
  run_synthesis: {
    label: 'Synthesis Analyst',
    description: 'Drafting core investment brief sections (Executive Summary, Business Overview, Risks, Verdict) using LLM.',
    color: '#10b981', // Emerald
  },
  run_risk_check: {
    label: 'Verification & Risk Auditor',
    description: 'Validating numerical claims in the synthesized brief against scraped/quant raw data.',
    color: '#f59e0b', // Amber
  },
  await_human_review: {
    label: 'Analyst Cockpit Intercept',
    description: 'Paused for manual verification, annotations, and approval decisions.',
    color: '#ef4444', // Red
  },
  loop_back_synthesis: {
    label: 'Revision Loop Trigger',
    description: 'Auto-rejection caught. Adjusting prompts and re-routing back to Synthesis.',
    color: '#ec4899', // Pink
  },
  abort_max_revisions: {
    label: 'Max Loops Abort',
    description: 'Research process terminated because loop limit exceeded.',
    color: '#6b7280', // Gray
  },
};

// Default standard list of tickers for suggestions in New Research form
export const TICKER_SUGGESTIONS = [
  'AAPL', 'MSFT', 'GOOG', 'AMZN', 'META', 'NVDA', 'NFLX', 
  'JPM', 'BAC', 'GS', 'MS', 
  'WMT', 'TGT', 'COST', 'HD'
];

// Local storage keys
export const STORAGE_KEYS = {
  AUTH_TOKEN: 'financial_analyst_auth_token',
  USER_INFO: 'financial_analyst_user_info',
  THEME_MODE: 'financial_analyst_theme_mode',
};
