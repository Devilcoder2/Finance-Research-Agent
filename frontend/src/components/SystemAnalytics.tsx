import { useState, useEffect } from 'react';
import { api } from '../services/api';
import type { AnalyticsResponse } from '../services/api';
import { BarChart3, TrendingUp, DollarSign, Activity, Award, ShieldCheck, RefreshCw } from 'lucide-react';

export function SystemAnalytics() {
  const [analytics, setAnalytics] = useState<AnalyticsResponse | null>(null);
  const [briefsEvaluations, setBriefsEvaluations] = useState<{
    ticker: string;
    threadName: string;
    score_factual: number;
    score_clarity: number;
    score_coverage: number;
    justification: string;
  }[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalyticsData = async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    setError(null);
    try {
      const analyticsData = await api.getAnalytics();
      setAnalytics(analyticsData);

      const threadsData = await api.getThreads();
      const completed = threadsData.filter(t => t.status === 'completed');

      // Fetch evaluations for completed threads
      const evalsList: typeof briefsEvaluations = [];
      const limitedThreads = completed.slice(0, 4); // Limit to top 4 recent completed threads to avoid rate limit/performance drops
      for (const t of limitedThreads) {
        try {
          const briefsList = await api.getBriefs(t.thread_id);
          briefsList.forEach(b => {
            if (b.evaluations && b.evaluations.length > 0) {
              evalsList.push({
                ticker: b.ticker,
                threadName: t.name,
                score_factual: b.evaluations[0].score_factual,
                score_clarity: b.evaluations[0].score_clarity,
                score_coverage: b.evaluations[0].score_coverage,
                justification: b.evaluations[0].rubric_justification
              });
            }
          });
        } catch (briefErr) {
          console.error(`Error loading briefs evaluations for thread ${t.thread_id}:`, briefErr);
        }
      }
      setBriefsEvaluations(evalsList);
    } catch (err: any) {
      console.error(err);
      setError('Failed to fetch analytics datasets.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchAnalyticsData();
  }, []);

  const summary = analytics?.summary;
  const details = analytics?.details || [];

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* Mini Controls Row */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
        <button 
          className="btn-secondary" 
          onClick={() => fetchAnalyticsData(true)} 
          disabled={loading || refreshing}
          style={{ padding: '8px 14px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px' }}
        >
          <RefreshCw size={14} className={refreshing ? 'animate-spin-slow' : ''} />
          <span>{refreshing ? 'Refreshing...' : 'Refresh Logs'}</span>
        </button>
      </div>

      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '64px 0', gap: '16px' }}>
          <div style={{ width: '40px', height: '40px', border: '3px solid rgba(255,255,255,0.05)', borderTopColor: 'var(--primary-glow)', borderRadius: '50%' }} className="animate-spin-slow" />
          <span style={{ color: 'var(--text-muted)', fontSize: '14px' }}>Compiling cost and performance statistics...</span>
        </div>
      ) : error ? (
        <div style={{ color: 'var(--accent-danger)', textAlign: 'center', padding: '40px' }}>{error}</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
          
          {/* Summary counters grid */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '20px'
          }}>
            <div className="glass-panel" style={{ padding: '24px' }}>
              <div style={{ display: 'flex', justifySelf: 'stretch', justifyContent: 'space-between', alignItems: 'center', color: 'var(--text-muted)' }}>
                <span style={{ fontSize: '13px' }}>Total Amount Spent</span>
                <DollarSign size={18} style={{ color: 'var(--secondary-glow)' }} />
              </div>
              <div style={{ fontSize: '28px', fontWeight: 800, color: 'var(--text-bright)', marginTop: '8px' }}>
                ${summary?.total_cost_usd.toFixed(4) || '0.00'}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                Based on active AI models cost
              </div>
            </div>

            <div className="glass-panel" style={{ padding: '24px' }}>
              <div style={{ display: 'flex', justifySelf: 'stretch', justifyContent: 'space-between', alignItems: 'center', color: 'var(--text-muted)' }}>
                <span style={{ fontSize: '13px' }}>AI Processing Volume</span>
                <BarChart3 size={18} style={{ color: 'var(--primary-glow)' }} />
              </div>
              <div style={{ fontSize: '24px', fontWeight: 800, color: 'var(--text-bright)', marginTop: '8px' }}>
                {((summary?.total_prompt_tokens || 0) + (summary?.total_completion_tokens || 0)).toLocaleString()}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                Inputs: {summary?.total_prompt_tokens.toLocaleString()} | Outputs: {summary?.total_completion_tokens.toLocaleString()}
              </div>
            </div>

            <div className="glass-panel" style={{ padding: '24px' }}>
              <div style={{ display: 'flex', justifySelf: 'stretch', justifyContent: 'space-between', alignItems: 'center', color: 'var(--text-muted)' }}>
                <span style={{ fontSize: '13px' }}>Average Research Speed</span>
                <Activity size={18} style={{ color: 'var(--accent-warning)' }} />
              </div>
              <div style={{ fontSize: '28px', fontWeight: 800, color: 'var(--text-bright)', marginTop: '8px' }}>
                {summary?.average_latency_seconds.toFixed(2) || '0.00'}s
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                Average time taken per report
              </div>
            </div>

            <div className="glass-panel" style={{ padding: '24px' }}>
              <div style={{ display: 'flex', justifySelf: 'stretch', justifyContent: 'space-between', alignItems: 'center', color: 'var(--text-muted)' }}>
                <span style={{ fontSize: '13px' }}>Total Reports Generated</span>
                <TrendingUp size={18} style={{ color: 'var(--accent-success)' }} />
              </div>
              <div style={{ fontSize: '28px', fontWeight: 800, color: 'var(--text-bright)', marginTop: '8px' }}>
                {summary?.total_runs || 0}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                Completed research runs
              </div>
            </div>
          </div>

          {/* Two-Column Observability Grid */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1.2fr 1fr',
            gap: '32px',
            alignItems: 'start'
          }}>
            
            {/* LLM As Judge Quality Audits */}
            <div className="glass-panel" style={{ padding: '28px' }}>
              <h3 className="font-display" style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-bright)', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Award size={18} style={{ color: 'var(--primary-glow)' }} />
                <span>AI Quality Checker Assessments</span>
              </h3>

              {briefsEvaluations.length === 0 ? (
                <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '32px 0', fontSize: '13px' }}>
                  No quality evaluations recorded yet. Approve a draft to run checks.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                  {briefsEvaluations.map((ev, idx) => (
                    <div key={idx} className="glass-card" style={{ padding: '16px 20px', borderLeft: '3px solid var(--primary-glow)' }}>
                      <div style={{ display: 'flex', justifySelf: 'stretch', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                        <span style={{ fontWeight: 600, fontSize: '14px', color: 'var(--text-bright)' }}>
                          {ev.ticker} - {ev.threadName.split(': ')[1] || ev.threadName}
                        </span>
                        <div style={{ display: 'flex', gap: '12px', fontSize: '11px', fontWeight: 700 }}>
                          <span style={{ color: 'var(--accent-success)' }}>Accuracy: {ev.score_factual.toFixed(1)}/5.0</span>
                          <span style={{ color: 'var(--secondary-glow)' }}>Readability: {ev.score_clarity.toFixed(1)}/5.0</span>
                          <span style={{ color: 'var(--accent-warning)' }}>Risks Coverage: {ev.score_coverage.toFixed(1)}/5.0</span>
                        </div>
                      </div>
                      <p style={{ fontSize: '12px', lineHeight: '1.6', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                        "{ev.justification}"
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Run latency & Cost Details Table */}
            <div className="glass-panel" style={{ padding: '28px' }}>
              <h3 className="font-display" style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-bright)', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <ShieldCheck size={18} style={{ color: 'var(--secondary-glow)' }} />
                <span>Research Speed & Cost Log</span>
              </h3>

              {details.length === 0 ? (
                <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '32px 0', fontSize: '13px' }}>
                  No activity logs recorded.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', maxHeight: '380px', overflowY: 'auto' }}>
                  {details.map((det) => (
                    <div 
                      key={det.id}
                      style={{
                        padding: '12px 16px',
                        borderBottom: '1px solid var(--border-glass)',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        fontSize: '13px'
                      }}
                    >
                      <div>
                        <div style={{ color: 'var(--text-bright)', fontWeight: 500 }}>
                          {det.thread_name.split(': ')[1] || det.thread_name}
                        </div>
                        <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>
                          Process Size: {(det.prompt_tokens + det.completion_tokens).toLocaleString()} units
                        </div>
                      </div>

                      <div style={{ textAlign: 'right' }}>
                        <div style={{ color: 'var(--secondary-glow)', fontWeight: 600 }}>
                          {det.latency_seconds.toFixed(2)}s
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--accent-success)', marginTop: '2px' }}>
                          ${det.estimated_cost_usd.toFixed(4)}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

          </div>

        </div>
      )}
    </div>
  );
}
