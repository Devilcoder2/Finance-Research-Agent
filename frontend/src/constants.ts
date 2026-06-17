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
    label: 'Loading Past Research',
    description: 'Retrieving historical report findings and analyst preferences to guide current research.',
    color: '#a855f7', // Purple
  },
  run_scraper: {
    label: 'Gathering Latest Info',
    description: 'Searching recent news, press releases, and official SEC documents online.',
    color: '#3b82f6', // Blue
  },
  run_quant: {
    label: 'Checking Financial Data',
    description: 'Fetching stock price history, balance sheets, and key performance ratios.',
    color: '#06b6d4', // Cyan
  },
  run_synthesis: {
    label: 'Writing Report Drafts',
    description: 'Drafting summaries, business overview, risk analyses, and final recommendations.',
    color: '#10b981', // Emerald
  },
  run_risk_check: {
    label: 'Checking Fact Accuracy',
    description: 'Verifying that generated numbers and statements match official source files.',
    color: '#f59e0b', // Amber
  },
  await_human_review: {
    label: 'Needs Your Review',
    description: 'AI has finished the drafts and is waiting for your approval or correction feedback.',
    color: '#ef4444', // Red
  },
  loop_back_synthesis: {
    label: 'Applying Feedback',
    description: 'Revising report sections based on your corrections and suggestions.',
    color: '#ec4899', // Pink
  },
  abort_max_revisions: {
    label: 'Limit Reached',
    description: 'Research cancelled because the maximum of 3 revision attempts was reached.',
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
