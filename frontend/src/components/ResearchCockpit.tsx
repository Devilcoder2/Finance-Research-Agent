import React, { useState, useEffect, useRef } from 'react';
import { api } from '../services/api';
import { useSSE } from '../hooks/useSSE';
import { TICKER_SUGGESTIONS, AGENT_NODES } from '../constants';
import { ArrowRight, Cpu, AlertTriangle, CheckCircle, Terminal, ArrowLeft } from 'lucide-react';

interface ResearchCockpitProps {
  activeThreadId: string | null;
  activeTickers: string[];
  onStartSession: (threadId: string, tickers: string[]) => void;
  onNavigateBack: () => void;
  onEnterReview: (threadId: string, tickers: string[]) => void;
}

export function ResearchCockpit({
  activeThreadId,
  activeTickers,
  onStartSession,
  onNavigateBack,
  onEnterReview,
}: ResearchCockpitProps) {
  // Input form state
  const [tickerInput, setTickerInput] = useState('');
  const [tickersList, setTickersList] = useState<string[]>(activeTickers);
  const [loading, setLoading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [threadName, setThreadName] = useState('');
  const [showLogs, setShowLogs] = useState(false);

  // SSE Stream hook
  const {
    logs,
    activeNode,
    activeTool,
    streamedText,
    isStreaming,
    error: sseError,
    isCompleted,
    pendingInterrupts,
  } = useSSE(activeThreadId);

  const terminalEndRef = useRef<HTMLDivElement>(null);
  const logContainerRef = useRef<HTMLDivElement>(null);

  // Scroll terminal and logs to bottom
  useEffect(() => {
    if (terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [streamedText]);

  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  const addTicker = (ticker: string) => {
    const clean = ticker.trim().toUpperCase();
    if (!clean) return;
    if (tickersList.includes(clean)) {
      setTickerInput('');
      return;
    }
    setTickersList([...tickersList, clean]);
    setTickerInput('');
    setFormError(null);
  };

  const removeTicker = (index: number) => {
    setTickersList(tickersList.filter((_, idx) => idx !== index));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === ',' || e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      addTicker(tickerInput);
    }
  };

  const getTickerFriendlyName = (ticker: string) => {
    if (ticker === 'AAPL') return 'Apple (AAPL)';
    if (ticker === 'MSFT') return 'Microsoft (MSFT)';
    if (ticker === 'GOOG') return 'Google (GOOG)';
    if (ticker === 'AMZN') return 'Amazon (AMZN)';
    if (ticker === 'META') return 'Meta (META)';
    if (ticker === 'NVDA') return 'Nvidia (NVDA)';
    if (ticker === 'NFLX') return 'Netflix (NFLX)';
    if (ticker === 'JPM') return 'JPMorgan (JPM)';
    if (ticker === 'BAC') return 'Bank of America (BAC)';
    if (ticker === 'WMT') return 'Walmart (WMT)';
    if (ticker === 'TSLA') return 'Tesla (TSLA)';
    return ticker;
  };

  const handleLaunch = async () => {
    if (tickersList.length === 0) {
      setFormError('Please add at least one stock ticker to research.');
      return;
    }

    setLoading(true);
    setFormError(null);

    // Auto-generate name if empty
    const cleanName = threadName.trim() || `Research Study: ${tickersList.join(', ')} - ${new Date().toLocaleDateString()}`;

    try {
      const result = await api.startResearch(tickersList, cleanName);
      onStartSession(result.thread_id, tickersList);
    } catch (err: any) {
      console.error(err);
      setFormError('Failed to start research study on server. Please check connection.');
    } finally {
      setLoading(false);
    }
  };

  // Check if thread should route to interrupt review
  const hasInterrupt = pendingInterrupts.length > 0 || activeNode === 'await_human_review';

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
      
      {/* Cockpit Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        {!activeThreadId && (
          <button 
            className="btn-secondary" 
            onClick={onNavigateBack}
            style={{ padding: '8px 12px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          >
            <ArrowLeft size={16} />
          </button>
        )}
        <div>
          <h2 className="font-display" style={{ fontSize: '28px', fontWeight: 700, color: 'var(--text-bright)' }}>
            {activeThreadId ? 'AI Analyst Running...' : 'Start New AI Analyst Report'}
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '4px' }}>
            {activeThreadId 
              ? `The AI is currently researching: ${activeTickers.join(', ')}` 
              : 'Enter one or more stock tickers to run automated market and financial reports.'}
          </p>
        </div>
      </div>

      {!activeThreadId ? (
        /* ================= FORM STATE ================= */
        <div className="glass-panel" style={{ padding: '36px', display: 'flex', flexDirection: 'column', gap: '28px' }}>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <label htmlFor="threadName" style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-bright)' }}>
              Report Title (Optional)
            </label>
            <input
              id="threadName"
              type="text"
              placeholder="e.g. Technology Giants Q3 Review (will be auto-generated if left blank)"
              className="glass-input"
              value={threadName}
              onChange={(e) => setThreadName(e.target.value)}
              disabled={loading}
              style={{ width: '100%' }}
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <label style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-bright)' }}>
              Which companies do you want to research?
            </label>
            
            <div style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: '8px',
              padding: '8px',
              backgroundColor: 'rgba(17, 24, 39, 0.5)',
              border: '1px solid var(--border-glass)',
              borderRadius: 'var(--border-radius-sm)',
              minHeight: '52px',
              alignItems: 'center',
            }}>
              {tickersList.map((ticker, idx) => (
                <span 
                  key={ticker} 
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '4px 10px',
                    fontSize: '13px',
                    fontWeight: 600,
                    backgroundColor: 'rgba(139, 92, 246, 0.12)',
                    border: '1px solid rgba(139, 92, 246, 0.3)',
                    color: 'var(--text-bright)',
                    borderRadius: '4px',
                  }}
                >
                  <span>{ticker}</span>
                  <button 
                    onClick={() => removeTicker(idx)} 
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--text-muted)',
                      cursor: 'pointer',
                      fontSize: '11px',
                      fontWeight: 700,
                      display: 'flex',
                      alignItems: 'center',
                    }}
                  >
                    ×
                  </button>
                </span>
              ))}
                            <input
                type="text"
                placeholder={tickersList.length === 0 ? "Type stock ticker (e.g. AAPL) and press Enter" : ""}
                value={tickerInput}
                onChange={(e) => setTickerInput(e.target.value)}
                onKeyDown={handleKeyDown}
                onBlur={() => addTicker(tickerInput)}
                style={{
                  background: 'none',
                  border: 'none',
                  outline: 'none',
                  color: 'var(--text-bright)',
                  fontSize: '14px',
                  padding: '4px 8px',
                  flexGrow: 1,
                  minWidth: '200px'
                }}
              />
            </div>
            
            {formError && (
              <div style={{ fontSize: '13px', color: 'var(--accent-danger)', marginTop: '4px' }}>
                {formError}
              </div>
            )}
          </div>

          {/* Suggestions */}
          <div>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '10px' }}>
              Popular Companies Suggestions
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {TICKER_SUGGESTIONS.map((sug) => {
                const added = tickersList.includes(sug);
                return (
                  <button
                    key={sug}
                    onClick={() => added ? setTickersList(tickersList.filter(t => t !== sug)) : addTicker(sug)}
                    className="btn-secondary"
                    style={{
                      padding: '6px 12px',
                      fontSize: '12px',
                      borderRadius: '4px',
                      backgroundColor: added ? 'rgba(6, 182, 212, 0.12)' : 'rgba(255, 255, 255, 0.02)',
                      borderColor: added ? 'rgba(6, 182, 212, 0.4)' : 'var(--border-glass)',
                      color: added ? 'var(--secondary-glow)' : 'var(--text-normal)'
                    }}
                  >
                    {getTickerFriendlyName(sug)}
                  </button>
                );
              })}
            </div>
          </div>

          <button
            className="btn-premium animate-glow-purple"
            onClick={handleLaunch}
            disabled={loading}
            style={{ alignSelf: 'flex-start', padding: '14px 28px', fontSize: '15px' }}
          >
            {loading ? 'Preparing AI Team...' : 'Start AI Research'}
            <ArrowRight size={16} />
          </button>
        </div>
      ) : (        /* ================= ACTIVE SSE STREAMING STATE ================= */
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          
          {/* Node Roadmap Progress bar */}
          <div className="glass-panel" style={{ padding: '24px' }}>
            <h3 style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '16px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              AI Team Progress Timeline
            </h3>
            
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              position: 'relative',
              gap: '12px',
              flexWrap: 'wrap',
            }}>
              {Object.keys(AGENT_NODES).map((nodeKey, idx) => {
                const nodeVal = AGENT_NODES[nodeKey];
                
                // Map custom node state outputs from backend labels
                const nodeIsActive = activeNode === nodeKey || 
                                     (nodeKey === 'run_scraper' && activeNode === 'scraper') ||
                                     (nodeKey === 'run_quant' && activeNode === 'quant') ||
                                     (nodeKey === 'run_synthesis' && activeNode === 'synthesis') ||
                                     (nodeKey === 'run_risk_check' && activeNode === 'risk_check');
                
                const nodeIsCompleted = isCompleted || 
                  (idx === 0 && activeNode !== 'load_memories' && activeNode !== null) ||
                  (idx === 1 && activeNode !== 'scraper' && activeNode !== 'load_memories' && activeNode !== null) ||
                  (idx === 2 && activeNode !== 'quant' && activeNode !== 'scraper' && activeNode !== 'load_memories' && activeNode !== null) ||
                  (idx === 3 && activeNode !== 'synthesis' && activeNode !== 'quant' && activeNode !== 'scraper' && activeNode !== 'load_memories' && activeNode !== null) ||
                  (idx === 4 && activeNode !== 'risk_check' && activeNode !== 'synthesis' && activeNode !== 'quant' && activeNode !== 'scraper' && activeNode !== 'load_memories' && activeNode !== null);

                let outlineGlow = 'rgba(255, 255, 255, 0.05)';

                if (nodeIsActive) {
                  outlineGlow = nodeVal.color;
                } else if (nodeIsCompleted) {
                  outlineGlow = 'var(--accent-success)';
                }

                return (
                  <div 
                    key={nodeKey} 
                    className="glass-card"
                    style={{
                      flex: '1',
                      minWidth: '160px',
                      padding: '16px',
                      border: `1px solid ${outlineGlow}40`,
                      borderRadius: 'var(--border-radius-sm)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '8px',
                      position: 'relative',
                      backgroundColor: nodeIsActive ? 'rgba(255, 255, 255, 0.02)' : 'rgba(17, 24, 39, 0.3)'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{
                        width: '8px',
                        height: '8px',
                        borderRadius: '50%',
                        backgroundColor: nodeIsCompleted ? 'var(--accent-success)' : (nodeIsActive ? nodeVal.color : 'var(--text-dark)'),
                        boxShadow: nodeIsActive ? `0 0 10px ${nodeVal.color}` : 'none'
                      }} />
                      {nodeIsCompleted && <CheckCircle size={14} style={{ color: 'var(--accent-success)' }} />}
                      {nodeIsActive && <Cpu size={14} style={{ color: nodeVal.color }} />}
                    </div>

                    <div style={{
                      fontWeight: 600,
                      fontSize: '13px',
                      color: nodeIsActive || nodeIsCompleted ? 'var(--text-bright)' : 'var(--text-muted)'
                    }}>
                      {nodeVal.label}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Friendly Active Spinner Card */}
          {!isCompleted && !hasInterrupt && !sseError && (
            <div className="glass-panel" style={{ padding: '40px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '24px' }}>
              <div style={{
                width: '56px',
                height: '56px',
                border: '4px solid rgba(139, 92, 246, 0.15)',
                borderTopColor: 'var(--primary-glow)',
                borderRadius: '50%',
              }} className="animate-spin-slow" />
              
              <div style={{ textAlign: 'center' }}>
                <h4 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-bright)' }}>
                  {activeNode && AGENT_NODES[activeNode] ? AGENT_NODES[activeNode].label : 'Starting AI Research...'}
                </h4>
                <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '8px', maxWidth: '500px', marginInline: 'auto' }}>
                  {activeNode && AGENT_NODES[activeNode] ? AGENT_NODES[activeNode].description : 'Setting up variables and launching online scrapers.'}
                </p>
                <div style={{ color: 'var(--secondary-glow)', fontSize: '12px', marginTop: '16px', fontWeight: 500 }}>
                  This process usually takes about 1-2 minutes.
                </div>
              </div>
            </div>
          )}

          {/* Active Error State Banner */}
          {(sseError || formError) && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.25)',
              borderRadius: 'var(--border-radius-sm)',
              padding: '16px 20px',
              color: 'var(--accent-danger)',
              fontSize: '14px',
            }}>
              <AlertTriangle size={20} style={{ flexShrink: 0 }} />
              <div>
                <strong>Something went wrong: </strong>
                {sseError || formError}
              </div>
            </div>
          )}

          {/* Collapsible advanced technical logger drawer */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '12px' }}>
            <button 
              className="btn-secondary" 
              onClick={() => setShowLogs(!showLogs)}
              style={{ alignSelf: 'center', fontSize: '13px', padding: '8px 16px' }}
            >
              {showLogs ? 'Hide Technical AI Logs (Advanced)' : 'Show Technical AI Logs (Advanced)'}
            </button>
            
            {showLogs && (
              <div style={{
                display: 'grid',
                gridTemplateColumns: '1fr',
                gap: '24px',
                alignItems: 'stretch'
              }}>
                {/* SSE Logger console */}
                <div className="glass-panel" style={{
                  display: 'flex',
                  flexDirection: 'column',
                  height: '300px',
                  overflow: 'hidden',
                  padding: '24px',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                    <h3 className="font-display" style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-bright)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Terminal size={16} />
                      <span>Activity Log Details</span>
                    </h3>
                    {activeTool && (
                      <span style={{ fontSize: '12px', color: 'var(--secondary-glow)', backgroundColor: 'rgba(6, 182, 212, 0.08)', padding: '2px 8px', borderRadius: '4px', border: '1px dashed rgba(6, 182, 212, 0.2)' }}>
                        Running Tool: {activeTool}
                      </span>
                    )}
                  </div>
                  
                  <div 
                    ref={logContainerRef}
                    style={{
                      flexGrow: 1,
                      overflowY: 'auto',
                      fontFamily: 'var(--font-mono)',
                      fontSize: '12px',
                      lineHeight: '1.6',
                      color: 'var(--text-normal)',
                      backgroundColor: 'rgba(0, 0, 0, 0.3)',
                      border: '1px solid var(--border-glass)',
                      borderRadius: '4px',
                      padding: '16px',
                    }}
                  >
                    {logs.length === 0 ? (
                      <div style={{ color: 'var(--text-dark)', padding: '24px 0', textAlign: 'center' }}>
                        Initializing data streams... Awaiting AI analyst signal.
                      </div>
                    ) : (
                      logs.map((log, index) => {
                        let typeColor = 'var(--text-muted)';
                        if (log.type === 'node') typeColor = 'var(--primary-glow)';
                        else if (log.type === 'tool') typeColor = 'var(--secondary-glow)';
                        else if (log.type === 'error') typeColor = 'var(--accent-danger)';
                        else if (log.type === 'system') typeColor = 'var(--accent-success)';

                        return (
                          <div key={index} style={{ marginBottom: '8px', borderBottom: '1px solid rgba(255, 255, 255, 0.01)', paddingBottom: '4px' }}>
                            <span style={{ color: 'var(--text-dark)', marginRight: '10px' }}>[{log.timestamp}]</span>
                            <span style={{ color: typeColor, fontWeight: 600, marginRight: '10px' }}>[{log.type.toUpperCase()}]</span>
                            <span>{log.message}</span>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>

                {/* Streamed thoughts terminal */}
                <div className="glass-panel" style={{
                  display: 'flex',
                  flexDirection: 'column',
                  height: '340px',
                  overflow: 'hidden',
                  padding: '24px',
                }}>
                  <h3 className="font-display" style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-bright)', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Cpu size={16} />
                    <span>Live Output Streaming Details</span>
                  </h3>
                  
                  <div style={{
                    flexGrow: 1,
                    overflowY: 'auto',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '13px',
                    lineHeight: '1.7',
                    color: 'var(--secondary-glow)',
                    backgroundColor: '#05070c',
                    border: '1px solid var(--border-glass)',
                    borderRadius: '4px',
                    padding: '20px',
                    whiteSpace: 'pre-wrap',
                  }}>
                    {streamedText ? (
                      <>
                        {streamedText}
                        {isStreaming && <span className="terminal-cursor" />}
                      </>
                    ) : (
                      <div style={{ color: 'var(--text-dark)', fontStyle: 'italic' }}>
                        {isStreaming 
                          ? 'Analyzing metrics... Preparing drafts.' 
                          : 'Terminal idle. Waiting for Synthesis step.'}
                      </div>
                    )}
                    <div ref={terminalEndRef} />
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Action buttons following complete or interrupt status */}
          {(isCompleted || hasInterrupt || sseError) && (
            <div className="glass-panel animate-fade-in" style={{
              padding: '24px 32px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              backgroundColor: hasInterrupt ? 'rgba(245, 158, 11, 0.04)' : 'rgba(16, 185, 129, 0.04)',
              borderColor: hasInterrupt ? 'rgba(245, 158, 11, 0.15)' : 'rgba(16, 185, 129, 0.15)',
            }}>
              <div>
                <h4 style={{ color: 'var(--text-bright)', fontWeight: 600, fontSize: '15px' }}>
                  {hasInterrupt 
                    ? 'AI Report Draft Ready for Review' 
                    : (isCompleted ? 'AI Research Report Completed' : 'Session Terminated')}
                </h4>
                <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginTop: '4px' }}>
                  {hasInterrupt 
                    ? `The AI has compiled a draft report for ${activeTickers.join(', ')}. Please review and approve the details.` 
                    : (isCompleted ? 'The final reports have been generated, evaluated, and saved successfully.' : 'An error occurred during agent routing.')}
                </p>
              </div>

              <div style={{ display: 'flex', gap: '12px' }}>
                <button className="btn-secondary" onClick={onNavigateBack}>
                  Return to Dashboard
                </button>
                {hasInterrupt && (
                  <button 
                    className="btn-premium animate-glow-purple"
                    onClick={() => onEnterReview(activeThreadId!, activeTickers)}
                  >
                    Open Report Viewer
                    <ArrowRight size={16} />
                  </button>
                )}
                {isCompleted && (
                  <button 
                    className="btn-premium animate-glow-cyan"
                    style={{ background: 'linear-gradient(135deg, var(--secondary-glow) 0%, hsl(187, 85%, 38%) 100%)', boxShadow: '0 4px 15px rgba(6, 182, 212, 0.3)' }}
                    onClick={() => onEnterReview(activeThreadId!, activeTickers)}
                  >
                    View Final Report
                    <ArrowRight size={16} />
                  </button>
                )}
              </div>
            </div>
          )}

        </div>
      )}

    </div>
  );
}
