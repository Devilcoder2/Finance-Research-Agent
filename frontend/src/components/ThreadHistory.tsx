import { useState, useEffect } from 'react';
import { api } from '../services/api';
import type { ThreadItem } from '../services/api';
import { Search, Filter, ArrowUpDown, Play, RefreshCw, Eye, ClipboardList, FileText } from 'lucide-react';

interface ThreadHistoryProps {
  onSelectThread: (threadId: string, tickers: string[]) => void;
  onNavigateToCockpit: (threadId: string, tickers: string[]) => void;
}

export function ThreadHistory({ onSelectThread, onNavigateToCockpit }: ThreadHistoryProps) {
  const [threads, setThreads] = useState<ThreadItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Search & Filter State
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc');

  const fetchThreads = async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    setError(null);
    try {
      const data = await api.getThreads();
      setThreads(data);
    } catch (err: any) {
      console.error(err);
      setError('Failed to fetch research threads.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchThreads();
  }, []);

  const handleSortToggle = () => {
    setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc');
  };

  // Filter & Sort logic
  const filteredThreads = threads
    .filter((t) => {
      const matchesSearch = 
        t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        t.tickers.some(tick => tick.toLowerCase().includes(searchQuery.toLowerCase()));
      
      const matchesStatus = statusFilter === 'all' || t.status === statusFilter;

      return matchesSearch && matchesStatus;
    })
    .sort((a, b) => {
      const dateA = new Date(a.created_at).getTime();
      const dateB = new Date(b.created_at).getTime();
      return sortOrder === 'desc' ? dateB - dateA : dateA - dateB;
    });

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 className="font-display" style={{ fontSize: '28px', fontWeight: 700, color: 'var(--text-bright)' }}>
            Thread History Explorer
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '4px' }}>
            Filter, search, and inspect past equity research sessions.
          </p>
        </div>
        
        <button 
          className="btn-secondary" 
          onClick={() => fetchThreads(true)} 
          disabled={loading || refreshing}
          style={{ padding: '10px 16px', display: 'flex', alignItems: 'center', gap: '8px' }}
        >
          <RefreshCw size={16} className={refreshing ? 'animate-spin-slow' : ''} />
          <span>{refreshing ? 'Reloading...' : 'Sync List'}</span>
        </button>
      </div>

      {/* Filter Panel */}
      <div className="glass-panel" style={{
        padding: '20px 24px',
        display: 'flex',
        gap: '16px',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap'
      }}>
        
        <div style={{ display: 'flex', gap: '16px', flexGrow: 1, maxWidth: '600px' }}>
          {/* Search box */}
          <div style={{ position: 'relative', flexGrow: 1 }}>
            <Search size={16} style={{ position: 'absolute', left: '16px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Search by Thread Name or Ticker..."
              className="glass-input"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ width: '100%', paddingLeft: '44px', paddingRight: '16px', height: '40px' }}
            />
          </div>

          {/* Status selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: '160px' }}>
            <Filter size={16} style={{ color: 'var(--text-muted)' }} />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="glass-input"
              style={{
                height: '40px',
                padding: '8px 12px',
                fontSize: '13px',
                backgroundColor: 'rgb(17, 24, 39)',
                cursor: 'pointer',
                flexGrow: 1,
              }}
            >
              <option value="all">All Statuses</option>
              <option value="completed">Completed</option>
              <option value="paused">Review Required</option>
              <option value="initiated">Running</option>
              <option value="failed">Failed</option>
            </select>
          </div>
        </div>

        {/* Sort order toggle */}
        <button 
          className="btn-secondary" 
          onClick={handleSortToggle}
          style={{ height: '40px', padding: '0 16px', display: 'flex', alignItems: 'center', gap: '8px' }}
        >
          <ArrowUpDown size={14} />
          <span>Sort Date: {sortOrder === 'desc' ? 'Newest' : 'Oldest'}</span>
        </button>

      </div>

      {/* History table */}
      <div className="glass-panel" style={{ padding: '24px', overflow: 'hidden' }}>
        {loading ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '64px 0', gap: '16px' }}>
            <div style={{ width: '36px', height: '36px', border: '3px solid rgba(255,255,255,0.05)', borderTopColor: 'var(--primary-glow)', borderRadius: '50%' }} className="animate-spin-slow" />
            <span style={{ color: 'var(--text-muted)', fontSize: '13px' }}>Syncing history records...</span>
          </div>
        ) : error ? (
          <div style={{ color: 'var(--accent-danger)', textAlign: 'center', padding: '40px' }}>{error}</div>
        ) : filteredThreads.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '48px', fontSize: '14px' }}>
            No matching threads found in logs database.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-glass)' }}>
                  <th style={{ padding: '12px 16px', color: 'var(--text-bright)', fontSize: '13px', fontWeight: 600 }}>Thread Name</th>
                  <th style={{ padding: '12px 16px', color: 'var(--text-bright)', fontSize: '13px', fontWeight: 600 }}>Tickers</th>
                  <th style={{ padding: '12px 16px', color: 'var(--text-bright)', fontSize: '13px', fontWeight: 600 }}>Creation Date</th>
                  <th style={{ padding: '12px 16px', color: 'var(--text-bright)', fontSize: '13px', fontWeight: 600 }}>Status</th>
                  <th style={{ padding: '12px 16px', color: 'var(--text-bright)', fontSize: '13px', fontWeight: 600 }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredThreads.map((thread) => {
                  let statusColor = 'var(--text-muted)';
                  let bgBadge = 'rgba(255, 255, 255, 0.03)';
                  let actionText = 'Open details';
                  let ActionIcon = Eye;

                  if (thread.status === 'completed') {
                    statusColor = 'var(--accent-success)';
                    bgBadge = 'rgba(16, 185, 129, 0.08)';
                    actionText = 'View Reports';
                    ActionIcon = FileText;
                  } else if (thread.status === 'paused' || thread.status === 'revision') {
                    statusColor = 'var(--accent-warning)';
                    bgBadge = 'rgba(245, 158, 11, 0.08)';
                    actionText = 'Resume Review';
                    ActionIcon = ClipboardList;
                  } else if (thread.status === 'initiated') {
                    statusColor = 'var(--accent-info)';
                    bgBadge = 'rgba(59, 130, 246, 0.08)';
                    actionText = 'Open Cockpit';
                    ActionIcon = Play;
                  } else if (thread.status === 'failed') {
                    statusColor = 'var(--accent-danger)';
                    bgBadge = 'rgba(239, 68, 68, 0.08)';
                  }

                  const handleAction = (e: React.MouseEvent) => {
                    e.stopPropagation();
                    if (thread.status === 'initiated') {
                      onNavigateToCockpit(thread.thread_id, thread.tickers);
                    } else {
                      onSelectThread(thread.thread_id, thread.tickers);
                    }
                  };

                  return (
                    <tr 
                      key={thread.thread_id}
                      className="glass-card"
                      style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.01)', cursor: 'pointer' }}
                      onClick={handleAction}
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
                                padding: '2px 6px',
                                fontSize: '11px',
                                borderRadius: '4px',
                                backgroundColor: 'rgba(255, 255, 255, 0.03)',
                                border: '1px solid var(--border-glass)',
                              }}
                            >
                              {t}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td style={{ padding: '16px', color: 'var(--text-muted)', fontSize: '13px' }}>
                        {new Date(thread.created_at).toLocaleDateString()} at {new Date(thread.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </td>
                      <td style={{ padding: '16px' }}>
                        <span style={{
                          padding: '3px 8px',
                          fontSize: '11px',
                          fontWeight: 700,
                          borderRadius: '12px',
                          color: statusColor,
                          backgroundColor: bgBadge,
                          border: `1px solid ${statusColor}18`,
                          textTransform: 'uppercase'
                        }}>
                          {thread.status === 'paused' || thread.status === 'revision' ? 'review required' : thread.status}
                        </span>
                      </td>
                      <td style={{ padding: '16px' }}>
                        <button
                          onClick={handleAction}
                          style={{
                            background: 'none',
                            border: 'none',
                            color: 'var(--primary-glow)',
                            fontWeight: 600,
                            fontSize: '13px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                          }}
                        >
                          <ActionIcon size={14} />
                          <span>{actionText}</span>
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
