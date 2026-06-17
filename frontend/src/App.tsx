import { useState, useEffect } from 'react';
import { DEFAULT_USER, STORAGE_KEYS } from './constants';
import { Login } from './components/Login';
import { Dashboard } from './components/Dashboard';
import { ResearchCockpit } from './components/ResearchCockpit';
import { BriefReview } from './components/BriefReview';
import { 
  FolderGit2, 
  Play, 
  LogOut, 
  User, 
  Cpu, 
  FileText,
  ChevronLeft,
  ChevronRight,
  Sun,
  Moon
} from 'lucide-react';

type TabType = 'dashboard' | 'new_research' | 'review';

export default function App() {
  const [currentUser, setCurrentUser] = useState<typeof DEFAULT_USER | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('dashboard');
  const [loading, setLoading] = useState(true);

  // Theme Controller state
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    const cached = localStorage.getItem(STORAGE_KEYS.THEME_MODE);
    return (cached as 'dark' | 'light') || 'dark';
  });

  // Collapsible Sidebar state
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Cockpit/Review state configurations
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [activeTickers, setActiveTickers] = useState<string[]>([]);
  
  // Staged Thread Id for Brief Review view
  const [reviewThreadId, setReviewThreadId] = useState<string | null>(null);
  const [reviewTickers, setReviewTickers] = useState<string[]>([]);

  // Sync theme selection to document.body
  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.THEME_MODE, theme);
    if (theme === 'light') {
      document.body.classList.add('light-theme');
    } else {
      document.body.classList.remove('light-theme');
    }
  }, [theme]);

  // Check auth cache on mount
  useEffect(() => {
    const cachedUser = localStorage.getItem(STORAGE_KEYS.USER_INFO);
    const cachedToken = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);

    if (cachedUser && cachedToken) {
      setCurrentUser(JSON.parse(cachedUser));
    }
    setLoading(false);
  }, []);

  const handleLoginSuccess = (user: typeof DEFAULT_USER) => {
    setCurrentUser(user);
    setActiveTab('dashboard');
  };

  const handleLogout = () => {
    localStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN);
    localStorage.removeItem(STORAGE_KEYS.USER_INFO);
    setCurrentUser(null);
    setActiveTab('dashboard');
    setActiveThreadId(null);
    setReviewThreadId(null);
  };

  // Navigates directly to review briefs
  const handleOpenReview = (threadId: string, tickers: string[]) => {
    setReviewThreadId(threadId);
    setReviewTickers(tickers);
    setActiveTab('review');
  };

  const handleSelectHistoryThread = (threadId: string, tickers: string[]) => {
    // Select this thread in review mode
    handleOpenReview(threadId, tickers);
  };

  // Trigger active running SSE cockpit thread
  const handleStartActiveResearch = (threadId: string, tickers: string[]) => {
    setActiveThreadId(threadId);
    setActiveTickers(tickers);
  };

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        backgroundColor: 'rgb(11, 15, 25)',
        color: 'var(--text-muted)',
      }}>
        <div style={{
          width: '32px',
          height: '32px',
          border: '3px solid rgba(139, 92, 246, 0.15)',
          borderTopColor: 'var(--primary-glow)',
          borderRadius: '50%',
        }} className="animate-spin-slow" />
      </div>
    );
  }

  if (!currentUser) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      
      {/* SIDEBAR NAVIGATION SHELL */}
      <aside className="glass-panel" style={{
        width: sidebarCollapsed ? '78px' : 'var(--sidebar-width)',
        minWidth: sidebarCollapsed ? '78px' : 'var(--sidebar-width)',
        borderRadius: '0',
        borderTop: '0',
        borderLeft: '0',
        borderBottom: '0',
        display: 'flex',
        flexDirection: 'column',
        padding: sidebarCollapsed ? '24px 8px' : '24px 16px',
        zIndex: 50,
        transition: 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
      }}>
        
        {/* Sidebar Header Logo & Collapse Button */}
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: sidebarCollapsed ? 'center' : 'space-between',
          padding: '0 8px 32px 8px', 
          borderBottom: '1px solid var(--border-glass)',
          flexWrap: 'nowrap'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              background: 'linear-gradient(135deg, var(--primary-glow) 0%, var(--secondary-glow) 100%)',
              borderRadius: '8px',
              padding: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 15px 0 rgba(139, 92, 246, 0.35)',
              flexShrink: 0
            }}>
              <Cpu size={20} style={{ color: 'var(--text-bright)' }} />
            </div>
            {!sidebarCollapsed && (
              <div>
                <h1 className="font-display" style={{ fontSize: '15px', fontWeight: 800, color: 'var(--text-bright)', letterSpacing: '-0.02em', margin: 0 }}>
                  AI Research Assistant
                </h1>
                <span style={{ fontSize: '9px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600, display: 'block', marginTop: '2px' }}>
                  Research Platform
                </span>
              </div>
            )}
          </div>
          
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            title={sidebarCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
            style={{
              background: 'rgba(255, 255, 255, 0.04)',
              border: '1px solid var(--border-glass)',
              borderRadius: '6px',
              width: '24px',
              height: '24px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              color: 'var(--text-muted)',
              marginLeft: sidebarCollapsed ? '0' : '8px',
              transition: 'all 0.2s ease',
              flexShrink: 0
            }}
          >
            {sidebarCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
          </button>
        </div>

        {/* Sidebar Nav Tabs */}
        <nav style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '32px', flexGrow: 1 }}>
          <button
            onClick={() => {
              setActiveTab('dashboard');
            }}
            title={sidebarCollapsed ? "Research Hub" : undefined}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: sidebarCollapsed ? 'center' : 'flex-start',
              gap: sidebarCollapsed ? '0' : '12px',
              padding: sidebarCollapsed ? '12px 0' : '12px 16px',
              fontSize: '14px',
              fontWeight: 500,
              borderRadius: 'var(--border-radius-sm)',
              border: 'none',
              cursor: 'pointer',
              outline: 'none',
              transition: 'all 0.2s ease',
              width: '100%',
              textAlign: 'left',
              backgroundColor: activeTab === 'dashboard' ? 'rgba(255, 255, 255, 0.04)' : 'transparent',
              color: activeTab === 'dashboard' ? 'var(--text-bright)' : 'var(--text-muted)',
              borderLeft: activeTab === 'dashboard' ? '3px solid var(--primary-glow)' : '3px solid transparent'
            }}
          >
            <FolderGit2 size={18} style={{ flexShrink: 0 }} />
            {!sidebarCollapsed && <span>Research Hub</span>}
          </button>

          <button
            onClick={() => {
              setActiveTab('new_research');
            }}
            title={sidebarCollapsed ? "Start AI Analyst" : undefined}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: sidebarCollapsed ? 'center' : 'flex-start',
              gap: sidebarCollapsed ? '0' : '12px',
              padding: sidebarCollapsed ? '12px 0' : '12px 16px',
              fontSize: '14px',
              fontWeight: 500,
              borderRadius: 'var(--border-radius-sm)',
              border: 'none',
              cursor: 'pointer',
              outline: 'none',
              transition: 'all 0.2s ease',
              width: '100%',
              textAlign: 'left',
              backgroundColor: activeTab === 'new_research' ? 'rgba(255, 255, 255, 0.04)' : 'transparent',
              color: activeTab === 'new_research' ? 'var(--text-bright)' : 'var(--text-muted)',
              borderLeft: activeTab === 'new_research' ? '3px solid var(--primary-glow)' : '3px solid transparent'
            }}
          >
            <Play size={18} fill={activeTab === 'new_research' ? "currentColor" : "none"} style={{ flexShrink: 0 }} />
            {!sidebarCollapsed && <span>Start AI Analyst</span>}
          </button>

          <button
            onClick={() => {
              setActiveTab('review');
            }}
            title={sidebarCollapsed ? "Report Viewer" : undefined}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: sidebarCollapsed ? 'center' : 'flex-start',
              gap: sidebarCollapsed ? '0' : '12px',
              padding: sidebarCollapsed ? '12px 0' : '12px 16px',
              fontSize: '14px',
              fontWeight: 500,
              borderRadius: 'var(--border-radius-sm)',
              border: 'none',
              cursor: 'pointer',
              outline: 'none',
              transition: 'all 0.2s ease',
              width: '100%',
              textAlign: 'left',
              backgroundColor: activeTab === 'review' ? 'rgba(255, 255, 255, 0.04)' : 'transparent',
              color: activeTab === 'review' ? 'var(--text-bright)' : 'var(--text-muted)',
              borderLeft: activeTab === 'review' ? '3px solid var(--primary-glow)' : '3px solid transparent'
            }}
          >
            <FileText size={18} style={{ flexShrink: 0 }} />
            {!sidebarCollapsed && <span>Report Viewer</span>}
          </button>
        </nav>

        {/* Sidebar Footer Profiles */}
        <div style={{
          marginTop: 'auto',
          borderTop: '1px solid var(--border-glass)',
          paddingTop: '20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
          alignItems: sidebarCollapsed ? 'center' : 'stretch'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: sidebarCollapsed ? 'center' : 'flex-start', gap: '12px' }}>
            <div style={{
              backgroundColor: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid var(--border-glass)',
              borderRadius: '50%',
              padding: '8px',
              color: 'var(--text-bright)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0
            }}>
              <User size={16} />
            </div>
            {!sidebarCollapsed && (
              <div style={{ overflow: 'hidden' }}>
                <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-bright)', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                  {currentUser.name}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                  {currentUser.email}
                </div>
              </div>
            )}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', width: '100%' }}>
            {/* Theme Toggle Button */}
            <button
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              title={sidebarCollapsed ? `Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode` : undefined}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: sidebarCollapsed ? '0' : '8px',
                padding: '10px',
                fontSize: '13px',
                fontWeight: 500,
                color: 'var(--text-bright)',
                backgroundColor: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid var(--border-glass)',
                borderRadius: 'var(--border-radius-sm)',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                width: '100%'
              }}
            >
              {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
              {!sidebarCollapsed && <span>{theme === 'dark' ? 'Light Theme' : 'Dark Theme'}</span>}
            </button>

            {/* Logout Button */}
            <button
              onClick={handleLogout}
              title={sidebarCollapsed ? "Sign Out" : undefined}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: sidebarCollapsed ? '0' : '8px',
                padding: '10px',
                fontSize: '13px',
                fontWeight: 500,
                color: 'var(--accent-danger)',
                backgroundColor: 'rgba(239, 68, 68, 0.03)',
                border: '1px solid rgba(239, 68, 68, 0.08)',
                borderRadius: 'var(--border-radius-sm)',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                width: '100%'
              }}
            >
              <LogOut size={14} />
              {!sidebarCollapsed && <span>Sign Out</span>}
            </button>
          </div>
        </div>

      </aside>

      {/* CENTRAL RESPONSIVE WORKSPACE WRAPPER */}
      <main style={{
        flexGrow: 1,
        height: '100vh',
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
      }}>
        
        {/* Workspace Top Header Widget */}
        <header className="glass-panel" style={{
          height: 'var(--header-height)',
          borderRadius: '0',
          borderTop: '0',
          borderRight: '0',
          borderLeft: '0',
          display: 'flex',
          justifyContent: 'flex-end',
          alignItems: 'center',
          padding: '0 32px',
          gap: '24px',
          zIndex: 40,
        }}>
          {activeThreadId && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              fontSize: '12px',
              backgroundColor: 'rgba(139, 92, 246, 0.08)',
              border: '1px dashed rgba(139, 92, 246, 0.2)',
              borderRadius: '4px',
              padding: '6px 12px',
              color: 'var(--primary-glow)',
              fontWeight: 500
            }}>
              <span style={{ display: 'inline-block', width: '6px', height: '6px', backgroundColor: 'var(--primary-glow)', borderRadius: '50%' }} className="animate-spin-slow" />
              <span>Research in Progress</span>
            </div>
          )}
          
          <div style={{
            fontSize: '12px',
            color: 'var(--text-muted)',
            backgroundColor: 'rgba(255, 255, 255, 0.03)',
            border: '1px solid var(--border-glass)',
            padding: '6px 12px',
            borderRadius: '4px',
            fontFamily: 'var(--font-mono)'
          }}>
            System Status: Connected & Stable
          </div>
        </header>

        {/* Central screen content container */}
        <div style={{ padding: '40px', maxWidth: '1200px', width: '100%', margin: '0 auto', flexGrow: 1 }}>
          
          {activeTab === 'dashboard' && (
            <Dashboard 
              onSelectThread={handleSelectHistoryThread}
              onNavigateToCockpit={() => setActiveTab('new_research')}
              onResumeRunningResearch={(threadId, tickers) => {
                handleStartActiveResearch(threadId, tickers);
                setActiveTab('new_research');
              }}
            />
          )}

          {activeTab === 'new_research' && (
            <ResearchCockpit 
              activeThreadId={activeThreadId}
              activeTickers={activeTickers}
              onStartSession={handleStartActiveResearch}
              onNavigateBack={() => {
                setActiveThreadId(null);
                setActiveTab('dashboard');
              }}
              onEnterReview={handleOpenReview}
            />
          )}

          {activeTab === 'review' && (
            reviewThreadId ? (
              <BriefReview 
                threadId={reviewThreadId}
                tickers={reviewTickers}
                onNavigateBack={() => {
                  setReviewThreadId(null);
                  setActiveTab('dashboard');
                }}
              />
            ) : (
              <div className="glass-panel animate-fade-in" style={{
                padding: '48px',
                textAlign: 'center',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '20px',
                minHeight: '350px',
                border: '1px dashed var(--border-glass)'
              }}>
                <div style={{
                  backgroundColor: 'rgba(139, 92, 246, 0.08)',
                  color: 'var(--primary-glow)',
                  borderRadius: '50%',
                  padding: '16px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: '8px'
                }}>
                  <FileText size={32} />
                </div>
                <h3 className="font-display" style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-bright)' }}>
                  No Active Report Selected
                </h3>
                <p style={{ color: 'var(--text-muted)', fontSize: '14px', maxWidth: '450px', lineHeight: '1.6', margin: 0 }}>
                  You have not selected a report to review yet. Go to the Research Hub to view completed past reports, or start a new analysis study.
                </p>
                <div style={{ display: 'flex', gap: '12px', marginTop: '8px' }}>
                  <button 
                    className="btn-secondary" 
                    onClick={() => setActiveTab('dashboard')}
                  >
                    Go to Research Hub
                  </button>
                  <button 
                    className="btn-premium" 
                    onClick={() => setActiveTab('new_research')}
                  >
                    Start AI Analyst
                  </button>
                </div>
              </div>
            )
          )}

        </div>

      </main>

    </div>
  );
}
