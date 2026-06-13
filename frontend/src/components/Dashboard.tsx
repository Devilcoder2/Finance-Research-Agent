import { useState, useEffect } from 'react';
import { api } from '../services/api';
import type { ThreadItem } from '../services/api';
import { Clock, DollarSign, FolderGit2, Play, RefreshCw, FileText } from 'lucide-react';

interface DashboardProps {
  onSelectThread: (threadId: string, tickers: string[]) => void;
  onNavigateToCockpit: () => void;
}

export function Dashboard({ onSelectThread, onNavigateToCockpit }: DashboardProps) {
  const [threads, setThreads] = useState<ThreadItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchThreads = async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    setError(null);
    try {
      const data = await api.getThreads();
      setThreads(data);
    } catch (err: any) {
      console.error(err);
      setError('Failed to fetch research threads. Ensure backend server is running.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchThreads();
  }, []);

  // Calculate aggregated stats
  const totalThreads = threads.length;
  const completedThreads = threads.filter(t => t.status === 'completed').length;
  const pendingReviews = threads.filter(t => t.status === 'paused' || t.status === 'revision').length;
  
  // Calculate mock estimate costs based on ticker counts for demo representation
  const totalTickersCount = threads.reduce((acc, t) => acc + (t.tickers?.length || 0), 0);
  const estimatedTotalCost = (totalTickersCount * 0.082).toFixed(2); // Mock: $0.082 per ticker

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
      
      {/* Overview Dashboard Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 className="font-display" style={{ fontSize: '28px', fontWeight: 700, color: 'var(--text-bright)' }}>
            Investment Workspace
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '4px' }}>
            Orchestrate multi-agent equity analysis runs and review drafts.
          </p>
        </div>
        
        <div style={{ display: 'flex', gap: '12px' }}>
          <button 
            className="btn-secondary" 
            onClick={() => fetchThreads(true)} 
            disabled={loading || refreshing}
            style={{ padding: '10px 16px', display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            <RefreshCw size={16} className={refreshing ? 'animate-spin-slow' : ''} />
            <span>{refreshing ? 'Reloading...' : 'Sync'}</span>
          </button>
          
          <button 
            className="btn-premium" 
            onClick={onNavigateToCockpit}
            style={{ padding: '10px 20px', display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            <Play size={16} fill="currentColor" />
            <span>New Session</span>
          </button>
        </div>
      </div>

      {/* Analytics Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
        gap: '20px'
      }}>
        <div className="glass-panel" style={{ padding: '24px', display: 'flex', alignItems: 'center', gap: '20px' }}>
          <div style={{
            backgroundColor: 'rgba(139, 92, 246, 0.1)',
            border: '1px solid rgba(139, 92, 246, 0.15)',
            borderRadius: '12px',
            padding: '12px',
            color: 'var(--primary-glow)',
          }}>
            <FolderGit2 size={24} />
          </div>
          <div>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Research Runs</div>
            <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--text-bright)', marginTop: '4px' }}>
              {totalThreads}
            </div>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '24px', display: 'flex', alignItems: 'center', gap: '20px' }}>
          <div style={{
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            border: '1px solid rgba(16, 185, 129, 0.15)',
            borderRadius: '12px',
            padding: '12px',
            color: 'var(--accent-success)',
          }}>
            <FileText size={24} />
          </div>
          <div>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Completed Briefs</div>
            <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--text-bright)', marginTop: '4px' }}>
              {completedThreads}
            </div>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '24px', display: 'flex', alignItems: 'center', gap: '20px' }}>
          <div style={{
            backgroundColor: 'rgba(245, 158, 11, 0.1)',
            border: '1px solid rgba(245, 158, 11, 0.15)',
            borderRadius: '12px',
            padding: '12px',
            color: 'var(--accent-warning)',
          }}>
            <Clock size={24} />
          </div>
          <div>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Pending Approvals</div>
            <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--text-bright)', marginTop: '4px' }}>
              {pendingReviews}
            </div>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '24px', display: 'flex', alignItems: 'center', gap: '20px' }}>
          <div style={{
            backgroundColor: 'rgba(6, 182, 212, 0.1)',
            border: '1px solid rgba(6, 182, 212, 0.15)',
            borderRadius: '12px',
            padding: '12px',
            color: 'var(--secondary-glow)',
          }}>
            <DollarSign size={24} />
          </div>
          <div>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Estimated API Cost</div>
            <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--text-bright)', marginTop: '4px' }}>
              ${estimatedTotalCost}
            </div>
          </div>
        </div>
      </div>

      {/* Workspace History Table */}
      <div className="glass-panel" style={{ padding: '28px', overflow: 'hidden' }}>
        <h3 className="font-display" style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-bright)', marginBottom: '20px' }}>
          Session History
        </h3>

        {loading ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '64px 0', gap: '16px' }}>
            <div style={{
              width: '40px',
              height: '40px',
              border: '3px solid rgba(139, 92, 246, 0.15)',
              borderTopColor: 'var(--primary-glow)',
              borderRadius: '50%',
            }} className="animate-spin-slow" />
            <span style={{ color: 'var(--text-muted)', fontSize: '14px' }}>Loading session records...</span>
          </div>
        ) : error ? (
          <div style={{
            textAlign: 'center',
            padding: '40px',
            color: 'var(--accent-danger)',
            backgroundColor: 'rgba(239, 68, 68, 0.03)',
            border: '1px dashed var(--border-glass)',
            borderRadius: 'var(--border-radius-sm)',
            fontSize: '14px'
          }}>
            {error}
          </div>
        ) : threads.length === 0 ? (
          <div style={{
            textAlign: 'center',
            padding: '64px',
            color: 'var(--text-muted)',
            border: '1px dashed var(--border-glass)',
            borderRadius: 'var(--border-radius-sm)',
            fontSize: '14px'
          }}>
            No research sessions found. Click "New Session" above to start.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-glass)', paddingBottom: '12px' }}>
                  <th style={{ padding: '12px 16px', color: 'var(--text-bright)', fontSize: '13px', fontWeight: 600 }}>Thread Name</th>
                  <th style={{ padding: '12px 16px', color: 'var(--text-bright)', fontSize: '13px', fontWeight: 600 }}>Analyzed Tickers</th>
                  <th style={{ padding: '12px 16px', color: 'var(--text-bright)', fontSize: '13px', fontWeight: 600 }}>Status</th>
                  <th style={{ padding: '12px 16px', color: 'var(--text-bright)', fontSize: '13px', fontWeight: 600 }}>Started Date</th>
                  <th style={{ padding: '12px 16px', color: 'var(--text-bright)', fontSize: '13px', fontWeight: 600 }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {threads.map((thread) => {
                  let statusBadgeColor = 'rgba(107, 114, 128, 0.1)';
                  let statusTextColor = 'var(--text-muted)';
                  let borderGlow = 'transparent';

                  switch (thread.status) {
                    case 'completed':
                      statusBadgeColor = 'rgba(16, 185, 129, 0.1)';
                      statusTextColor = 'var(--accent-success)';
                      break;
                    case 'paused':
                    case 'revision':
                      statusBadgeColor = 'rgba(245, 158, 11, 0.1)';
                      statusTextColor = 'var(--accent-warning)';
                      borderGlow = '0 0 10px rgba(245, 158, 11, 0.15)';
                      break;
                    case 'initiated':
                      statusBadgeColor = 'rgba(59, 130, 246, 0.1)';
                      statusTextColor = 'var(--accent-info)';
                      break;
                    case 'failed':
                      statusBadgeColor = 'rgba(239, 68, 68, 0.1)';
                      statusTextColor = 'var(--accent-danger)';
                      break;
                  }

                  return (
                    <tr 
                      key={thread.thread_id} 
                      className="glass-card"
                      style={{ 
                        borderBottom: '1px solid rgba(255, 255, 255, 0.02)',
                        cursor: 'pointer',
                      }}
                      onClick={() => onSelectThread(thread.thread_id, thread.tickers)}
                    >
                      <td style={{ padding: '16px', color: 'var(--text-bright)', fontSize: '14px', fontWeight: 500 }}>
                        {thread.name}
                      </td>
                      <td style={{ padding: '16px' }}>
                        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                          {thread.tickers?.map((t) => (
                            <span 
                              key={t}
                              style={{
                                padding: '3px 8px',
                                fontSize: '11px',
                                fontWeight: 600,
                                borderRadius: '4px',
                                backgroundColor: 'rgba(255, 255, 255, 0.05)',
                                color: 'var(--text-normal)',
                                border: '1px solid var(--border-glass)',
                              }}
                            >
                              {t}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td style={{ padding: '16px' }}>
                        <span style={{
                          padding: '4px 10px',
                          fontSize: '11px',
                          fontWeight: 600,
                          borderRadius: '12px',
                          backgroundColor: statusBadgeColor,
                          color: statusTextColor,
                          border: `1px solid ${statusTextColor}25`,
                          boxShadow: borderGlow,
                          textTransform: 'uppercase',
                        }}>
                          {thread.status}
                        </span>
                      </td>
                      <td style={{ padding: '16px', color: 'var(--text-muted)', fontSize: '13px' }}>
                        {new Date(thread.created_at).toLocaleDateString()} at {new Date(thread.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </td>
                      <td style={{ padding: '16px' }}>
                        <button
                          style={{
                            background: 'none',
                            border: 'none',
                            color: 'var(--primary-glow)',
                            fontWeight: 600,
                            fontSize: '13px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                          }}
                        >
                          <span>Open</span>
                          <Play size={10} fill="currentColor" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

    </div>
  );
}
