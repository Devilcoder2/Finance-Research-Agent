import { useState, useEffect } from 'react';
import { DEFAULT_USER, STORAGE_KEYS } from './constants';
import { Login } from './components/Login';
import { Dashboard } from './components/Dashboard';
import { ResearchCockpit } from './components/ResearchCockpit';
import { BriefReview } from './components/BriefReview';
import { Comparison } from './components/Comparison';
import { 
  FolderGit2, 
  Play, 
  BarChart3, 
  LogOut, 
  User, 
  Cpu, 
  FileText
} from 'lucide-react';

type TabType = 'dashboard' | 'new_research' | 'comparison' | 'review';

export default function App() {
  const [currentUser, setCurrentUser] = useState<typeof DEFAULT_USER | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('dashboard');
  const [loading, setLoading] = useState(true);

  // Cockpit/Review state configurations
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [activeTickers, setActiveTickers] = useState<string[]>([]);
  
  // Staged Thread Id for Brief Review view
  const [reviewThreadId, setReviewThreadId] = useState<string | null>(null);
  const [reviewTickers, setReviewTickers] = useState<string[]>([]);

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
        width: 'var(--sidebar-width)',
        borderRadius: '0',
        borderTop: '0',
        borderLeft: '0',
        borderBottom: '0',
        display: 'flex',
        flexDirection: 'column',
        padding: '24px 16px',
        zIndex: 50,
      }}>
        
        {/* Sidebar Header Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '0 8px 32px 8px', borderBottom: '1px solid var(--border-glass)' }}>
          <div style={{
            background: 'linear-gradient(135deg, var(--primary-glow) 0%, var(--secondary-glow) 100%)',
            borderRadius: '8px',
            padding: '8px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 15px 0 rgba(139, 92, 246, 0.35)'
          }}>
            <Cpu size={20} style={{ color: 'var(--text-bright)' }} />
          </div>
          <div>
            <h1 className="font-display" style={{ fontSize: '18px', fontWeight: 800, color: 'var(--text-bright)', letterSpacing: '-0.02em' }}>
              ANTIGRAVITY
            </h1>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>
              Research Cockpit
            </span>
          </div>
        </div>

        {/* Sidebar Nav Tabs */}
        <nav style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '32px', flexGrow: 1 }}>
          <button
            onClick={() => {
              setActiveTab('dashboard');
              setReviewThreadId(null);
            }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              padding: '12px 16px',
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
            <FolderGit2 size={18} />
            <span>Investment Board</span>
          </button>

          <button
            onClick={() => {
              setActiveTab('new_research');
              setReviewThreadId(null);
            }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              padding: '12px 16px',
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
            <Play size={18} fill={activeTab === 'new_research' ? "currentColor" : "none"} />
            <span>Launch Analysis</span>
          </button>

          <button
            onClick={() => {
              setActiveTab('comparison');
              setReviewThreadId(null);
            }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              padding: '12px 16px',
              fontSize: '14px',
              fontWeight: 500,
              borderRadius: 'var(--border-radius-sm)',
              border: 'none',
              cursor: 'pointer',
              outline: 'none',
              transition: 'all 0.2s ease',
              width: '100%',
              textAlign: 'left',
              backgroundColor: activeTab === 'comparison' ? 'rgba(255, 255, 255, 0.04)' : 'transparent',
              color: activeTab === 'comparison' ? 'var(--text-bright)' : 'var(--text-muted)',
              borderLeft: activeTab === 'comparison' ? '3px solid var(--primary-glow)' : '3px solid transparent'
            }}
          >
            <BarChart3 size={18} />
            <span>Metrics Analytics</span>
          </button>

          {/* Staged review view indicator if active */}
          {reviewThreadId && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '12px 16px',
                fontSize: '14px',
                fontWeight: 500,
                borderRadius: 'var(--border-radius-sm)',
                color: 'var(--accent-warning)',
                backgroundColor: 'rgba(245, 158, 11, 0.04)',
                borderLeft: '3px solid var(--accent-warning)'
              }}
            >
              <FileText size={18} />
              <span>Report Draft Review</span>
            </div>
          )}
        </nav>

        {/* Sidebar Footer Profiles */}
        <div style={{
          marginTop: 'auto',
          borderTop: '1px solid var(--border-glass)',
          paddingTop: '20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              backgroundColor: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid var(--border-glass)',
              borderRadius: '50%',
              padding: '8px',
              color: 'var(--text-bright)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <User size={16} />
            </div>
            <div style={{ overflow: 'hidden' }}>
              <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-bright)', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                {currentUser.name}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                {currentUser.email}
              </div>
            </div>
          </div>

          <button
            onClick={handleLogout}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
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
            <span>Sign Out</span>
          </button>
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
              <span>Active SSE Node Stream Active</span>
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
            Terminal CIK standard limit: 10 req/s
          </div>
        </header>

        {/* Central screen content container */}
        <div style={{ padding: '40px', maxWidth: '1200px', width: '100%', margin: '0 auto', flexGrow: 1 }}>
          
          {activeTab === 'dashboard' && (
            <Dashboard 
              onSelectThread={handleSelectHistoryThread}
              onNavigateToCockpit={() => setActiveTab('new_research')}
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

          {activeTab === 'review' && reviewThreadId && (
            <BriefReview 
              threadId={reviewThreadId}
              tickers={reviewTickers}
              onNavigateBack={() => {
                setReviewThreadId(null);
                setActiveTab('dashboard');
              }}
            />
          )}

          {activeTab === 'comparison' && (
            <Comparison 
              onNavigateBack={() => setActiveTab('dashboard')}
            />
          )}

        </div>

      </main>

    </div>
  );
}
