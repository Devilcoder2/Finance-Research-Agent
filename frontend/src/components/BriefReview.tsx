import { useState, useEffect } from 'react';
import { api } from '../services/api';
import type { BriefItem, SectionAnnotation } from '../services/api';
import { Award, Check, MessageSquare, ShieldAlert, X, CornerDownRight, RotateCcw } from 'lucide-react';

interface BriefReviewProps {
  threadId: string;
  tickers: string[];
  onNavigateBack: () => void;
}

export function BriefReview({ threadId, tickers, onNavigateBack }: BriefReviewProps) {
  const [briefs, setBriefs] = useState<BriefItem[]>([]);
  const [activeTicker, setActiveTicker] = useState<string>(tickers[0] || '');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Annotation states
  const [selectedSection, setSelectedSection] = useState<string | null>(null);
  const [commentInput, setCommentInput] = useState('');
  const [localAnnotations, setLocalAnnotations] = useState<Record<string, string[]>>({});
  
  // Submit actions states
  const [submitting, setSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null);

  const fetchBriefs = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getBriefs(threadId);
      setBriefs(data);
      if (data.length > 0 && !activeTicker) {
        setActiveTicker(data[0].ticker);
      }
    } catch (err: any) {
      console.error(err);
      setError('Could not load investment briefs. Check if thread has generated drafts.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBriefs();
  }, [threadId]);

  const activeBrief = briefs.find(b => b.ticker === activeTicker);

  const handleAddAnnotation = () => {
    if (!selectedSection || !commentInput.trim()) return;

    setLocalAnnotations(prev => {
      const current = prev[selectedSection] || [];
      return {
        ...prev,
        [selectedSection]: [...current, commentInput.trim()]
      };
    });
    setCommentInput('');
    setSelectedSection(null);
  };

  const handleRemoveAnnotation = (sectionId: string, idx: number) => {
    setLocalAnnotations(prev => {
      const current = prev[sectionId] || [];
      const updated = current.filter((_, i) => i !== idx);
      const copy = { ...prev, [sectionId]: updated };
      if (updated.length === 0) delete copy[sectionId];
      return copy;
    });
  };

  const handleSubmitDecision = async (action: 'approve' | 'reject') => {
    setSubmitting(true);
    setError(null);
    setSubmitSuccess(null);

    // Form annotations payload for rejection
    const feedbackPayload: SectionAnnotation[] = [];
    if (action === 'reject') {
      Object.keys(localAnnotations).forEach(sectionId => {
        localAnnotations[sectionId].forEach(comment => {
          feedbackPayload.push({ section_id: sectionId, comment });
        });
      });

      if (feedbackPayload.length === 0) {
        setError('Please add at least one annotation comment to reject the draft and request revision.');
        setSubmitting(false);
        return;
      }
    }

    try {
      const result = await api.resumeResearch(threadId, activeTicker, action, feedbackPayload);
      setSubmitSuccess(`Brief action "${action}" completed successfully. Status: ${result.status}`);
      setLocalAnnotations({});
      // Refresh briefs list
      await fetchBriefs();
    } catch (err: any) {
      console.error(err);
      setError(`Failed to submit decision: ${err.message || 'Server connection error.'}`);
    } finally {
      setSubmitting(false);
    }
  };

  // Sections of InvestmentBrief pydantic schema mapping to human labels
  const BRIEFS_SECTIONS = [
    { id: 'executive_summary', label: 'Executive Thesis Summary' },
    { id: 'business_overview', label: 'Business & Operations Model' },
    { id: 'financial_analysis', label: 'Quantitative & Financial Analysis' },
    { id: 'risk_factors', label: 'Downside Risk Matrix' },
    { id: 'verdict', label: 'Analyst Valuation & Recommendation' },
  ];

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
      
      {/* Review Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 className="font-display" style={{ fontSize: '28px', fontWeight: 700, color: 'var(--text-bright)' }}>
            Investment Reports cockpit
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '4px' }}>
            Review structured summaries, inspect auditor metrics, and execute approval triggers.
          </p>
        </div>
        
        <button className="btn-secondary" onClick={onNavigateBack}>
          Workspace Home
        </button>
      </div>

      {/* Multi-ticker tab headers */}
      {tickers.length > 1 && (
        <div style={{
          display: 'flex',
          borderBottom: '1px solid var(--border-glass)',
          gap: '8px',
          paddingBottom: '2px',
        }}>
          {tickers.map((t) => {
            const isActive = activeTicker === t;
            const briefItem = briefs.find(b => b.ticker === t);
            const statusLabel = briefItem ? 'Ready' : 'Pending';

            return (
              <button
                key={t}
                onClick={() => {
                  setActiveTicker(t);
                  setSubmitSuccess(null);
                  setError(null);
                }}
                style={{
                  background: 'none',
                  border: 'none',
                  outline: 'none',
                  cursor: 'pointer',
                  padding: '12px 24px',
                  fontWeight: 600,
                  fontSize: '14px',
                  color: isActive ? 'var(--text-bright)' : 'var(--text-muted)',
                  borderBottom: isActive ? '2px solid var(--primary-glow)' : '2px solid transparent',
                  transition: 'all 0.3s ease',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                <span>{t}</span>
                <span style={{
                  fontSize: '10px',
                  padding: '2px 6px',
                  borderRadius: '4px',
                  backgroundColor: isActive ? 'rgba(139, 92, 246, 0.12)' : 'rgba(255, 255, 255, 0.03)',
                  color: isActive ? 'var(--primary-glow)' : 'var(--text-muted)',
                }}>
                  {statusLabel}
                </span>
              </button>
            );
          })}
        </div>
      )}

      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '64px 0', gap: '16px' }}>
          <div style={{
            width: '40px',
            height: '40px',
            border: '3px solid rgba(139, 92, 246, 0.15)',
            borderTopColor: 'var(--primary-glow)',
            borderRadius: '50%',
          }} className="animate-spin-slow" />
          <span style={{ color: 'var(--text-muted)', fontSize: '14px' }}>Loading investment brief files...</span>
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
      ) : !activeBrief ? (
        <div style={{
          textAlign: 'center',
          padding: '64px',
          color: 'var(--text-muted)',
          border: '1px dashed var(--border-glass)',
          borderRadius: 'var(--border-radius-sm)',
          fontSize: '14px'
        }}>
          No brief exists for ticker "{activeTicker}" in this session.
        </div>
      ) : (
        /* ================= REVIEW CONTENT WORKSPACE ================= */
        <div style={{
          display: 'grid',
          gridTemplateColumns: '3fr 2fr',
          gap: '32px',
          alignItems: 'start'
        }}>
          
          {/* Brief Document Container */}
          <div className="glass-panel animate-fade-in" style={{ padding: '36px', display: 'flex', flexDirection: 'column', gap: '28px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-glass)', paddingBottom: '16px' }}>
              <div>
                <h3 className="font-display" style={{ fontSize: '22px', fontWeight: 700, color: 'var(--text-bright)' }}>
                  {activeBrief.ticker} Analyst Synthesis Brief
                </h3>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  Revision count: {activeBrief.revision_count} • Created at {new Date(activeBrief.created_at).toLocaleDateString()}
                </span>
              </div>
              
              <span style={{
                fontSize: '12px',
                padding: '4px 10px',
                backgroundColor: 'rgba(16, 185, 129, 0.12)',
                color: 'var(--accent-success)',
                fontWeight: 600,
                borderRadius: '4px',
                border: '1px solid rgba(16, 185, 129, 0.2)',
              }}>
                Synthesis Ready
              </span>
            </div>

            {/* Render Sections */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              {BRIEFS_SECTIONS.map((section: { id: string; label: string }) => {
                const sectionContent = activeBrief.brief_content[section.id as keyof typeof activeBrief.brief_content] || 'Section is drafting...';
                
                // Fetch annotations for this section
                const sectionLocalAnnotations = localAnnotations[section.id] || [];
                const savedAnnotations = activeBrief.annotations?.filter(a => a.section_id === section.id) || [];

                return (
                  <div 
                    key={section.id} 
                    className="glass-card"
                    onClick={() => {
                      setSelectedSection(section.id);
                      setCommentInput('');
                    }}
                    style={{
                      padding: '20px 24px',
                      cursor: 'pointer',
                      borderLeft: selectedSection === section.id ? '3px solid var(--primary-glow)' : '1px solid var(--border-glass)',
                      backgroundColor: selectedSection === section.id ? 'rgba(255, 255, 255, 0.01)' : 'rgba(17, 24, 39, 0.2)',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                      <h4 style={{ color: 'var(--text-bright)', fontWeight: 600, fontSize: '15px' }}>
                        {section.label}
                      </h4>
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <MessageSquare size={12} />
                        <span>Annotate</span>
                      </span>
                    </div>

                    <p style={{ 
                      fontSize: '14px', 
                      lineHeight: '1.7', 
                      color: 'var(--text-normal)',
                      whiteSpace: 'pre-wrap',
                    }}>
                      {sectionContent}
                    </p>

                    {/* Render existing annotations */}
                    {(savedAnnotations.length > 0 || sectionLocalAnnotations.length > 0) && (
                      <div style={{
                        marginTop: '16px',
                        padding: '12px 16px',
                        backgroundColor: 'rgba(0, 0, 0, 0.2)',
                        borderRadius: '4px',
                        borderLeft: '2px solid var(--accent-warning)',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '8px',
                      }} onClick={(e) => e.stopPropagation()}>
                        <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--accent-warning)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          Analyst Feedback Annotations:
                        </div>
                        {savedAnnotations.map((ann, idx) => (
                          <div key={idx} style={{ fontSize: '12px', color: 'var(--text-normal)', display: 'flex', alignItems: 'start', gap: '6px' }}>
                            <CornerDownRight size={12} style={{ color: 'var(--text-dark)', marginTop: '2px', flexShrink: 0 }} />
                            <span>{ann.comment} <span style={{ color: 'var(--text-dark)', fontSize: '10px' }}>({new Date(ann.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })})</span></span>
                          </div>
                        ))}
                        {sectionLocalAnnotations.map((comm, idx) => (
                          <div key={`local-${idx}`} style={{ fontSize: '12px', color: 'var(--text-bright)', display: 'flex', justifySelf: 'stretch', justifyContent: 'space-between', alignItems: 'start', gap: '10px' }}>
                            <div style={{ display: 'flex', alignItems: 'start', gap: '6px' }}>
                              <CornerDownRight size={12} style={{ color: 'var(--accent-warning)', marginTop: '2px', flexShrink: 0 }} />
                              <span>{comm} <span style={{ color: 'var(--accent-warning)', fontSize: '10px' }}>(Staged)</span></span>
                            </div>
                            <button 
                              onClick={() => handleRemoveAnnotation(section.id, idx)}
                              style={{ background: 'none', border: 'none', color: 'var(--accent-danger)', cursor: 'pointer' }}
                            >
                              <X size={12} />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}

                  </div>
                );
              })}
            </div>

          </div>

          {/* Side Audit Panel & Actions */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', position: 'sticky', top: '24px' }}>
            
            {/* LLM Evaluator scores */}
            {activeBrief.evaluations && activeBrief.evaluations.length > 0 && (
              <div className="glass-panel" style={{ padding: '24px' }}>
                <h3 className="font-display" style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-bright)', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                  <Award size={16} style={{ color: 'var(--secondary-glow)' }} />
                  <span>Auditor Judge Assessment</span>
                </h3>
                
                {activeBrief.evaluations.map((ev, index) => (
                  <div key={index} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Factual Accuracy</span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <div style={{ width: '80px', height: '6px', backgroundColor: 'rgba(255, 255, 255, 0.05)', borderRadius: '3px', overflow: 'hidden' }}>
                            <div style={{ width: `${(ev.score_factual / 5) * 100}%`, height: '100%', backgroundColor: 'var(--accent-success)' }} />
                          </div>
                          <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-bright)' }}>{ev.score_factual.toFixed(1)}/5.0</span>
                        </div>
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Narrative Clarity</span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <div style={{ width: '80px', height: '6px', backgroundColor: 'rgba(255, 255, 255, 0.05)', borderRadius: '3px', overflow: 'hidden' }}>
                            <div style={{ width: `${(ev.score_clarity / 5) * 100}%`, height: '100%', backgroundColor: 'var(--primary-glow)' }} />
                          </div>
                          <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-bright)' }}>{ev.score_clarity.toFixed(1)}/5.0</span>
                        </div>
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Downside Risk Coverage</span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <div style={{ width: '80px', height: '6px', backgroundColor: 'rgba(255, 255, 255, 0.05)', borderRadius: '3px', overflow: 'hidden' }}>
                            <div style={{ width: `${(ev.score_coverage / 5) * 100}%`, height: '100%', backgroundColor: 'var(--accent-warning)' }} />
                          </div>
                          <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-bright)' }}>{ev.score_coverage.toFixed(1)}/5.0</span>
                        </div>
                      </div>
                    </div>

                    <div style={{
                      backgroundColor: 'rgba(0, 0, 0, 0.2)',
                      border: '1px solid var(--border-glass)',
                      borderRadius: '4px',
                      padding: '12px 16px',
                      fontSize: '12px',
                      lineHeight: '1.6',
                      color: 'var(--text-normal)',
                      fontStyle: 'italic',
                    }}>
                      "{ev.rubric_justification}"
                    </div>

                  </div>
                ))}
              </div>
            )}

            {/* Inline Comment Input Box */}
            {selectedSection && (
              <div className="glass-panel animate-fade-in" style={{ padding: '24px', border: '1px solid rgba(139, 92, 246, 0.25)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <h4 style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-bright)' }}>
                    Add Comment for: <span style={{ color: 'var(--primary-glow)' }}>{BRIEFS_SECTIONS.find((s: { id: string; label: string }) => s.id === selectedSection)?.label}</span>
                  </h4>
                  <button 
                    onClick={() => setSelectedSection(null)}
                    style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
                  >
                    <X size={14} />
                  </button>
                </div>
                
                <textarea
                  placeholder="Specify factual discrepancies or instructions (e.g. Include details on recent earnings margin changes)..."
                  className="glass-input"
                  style={{ width: '100%', minHeight: '80px', fontSize: '13px', resize: 'vertical', marginBottom: '12px' }}
                  value={commentInput}
                  onChange={(e) => setCommentInput(e.target.value)}
                />

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                  <button className="btn-secondary" style={{ padding: '6px 12px', fontSize: '12px' }} onClick={() => setSelectedSection(null)}>
                    Cancel
                  </button>
                  <button className="btn-premium" style={{ padding: '6px 12px', fontSize: '12px' }} onClick={handleAddAnnotation}>
                    Staged Annotation
                  </button>
                </div>
              </div>
            )}

            {/* Decision Controls Card */}
            <div className="glass-panel" style={{ padding: '24px' }}>
              <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-bright)', marginBottom: '16px' }}>
                Decision Center
              </h3>

              {submitSuccess && (
                <div style={{
                  fontSize: '13px',
                  backgroundColor: 'rgba(16, 185, 129, 0.12)',
                  color: 'var(--accent-success)',
                  padding: '10px 14px',
                  border: '1px solid rgba(16, 185, 129, 0.2)',
                  borderRadius: '4px',
                  marginBottom: '16px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}>
                  <Check size={16} />
                  <span>{submitSuccess}</span>
                </div>
              )}

              {error && (
                <div style={{
                  fontSize: '13px',
                  backgroundColor: 'rgba(239, 68, 68, 0.12)',
                  color: 'var(--accent-danger)',
                  padding: '10px 14px',
                  border: '1px solid rgba(239, 68, 68, 0.2)',
                  borderRadius: '4px',
                  marginBottom: '16px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}>
                  <ShieldAlert size={16} />
                  <span>{error}</span>
                </div>
              )}

              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <button
                  className="btn-premium animate-glow-cyan"
                  style={{
                    width: '100%',
                    background: 'linear-gradient(135deg, var(--accent-success) 0%, hsl(156, 75%, 32%) 100%)',
                    boxShadow: '0 4px 15px rgba(16, 185, 129, 0.3)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                  }}
                  disabled={submitting}
                  onClick={() => handleSubmitDecision('approve')}
                >
                  <Check size={18} />
                  <span>{submitting ? 'Submitting decision...' : 'Authorize Publication'}</span>
                </button>

                <button
                  className="btn-secondary"
                  style={{
                    width: '100%',
                    border: '1px solid rgba(245, 158, 11, 0.3)',
                    color: 'var(--accent-warning)',
                    backgroundColor: 'rgba(245, 158, 11, 0.02)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                  }}
                  disabled={submitting}
                  onClick={() => handleSubmitDecision('reject')}
                >
                  <RotateCcw size={16} />
                  <span>Reject & Request Revision</span>
                </button>
              </div>

              <div style={{
                fontSize: '11px',
                color: 'var(--text-muted)',
                textAlign: 'center',
                lineHeight: '1.5',
                marginTop: '16px',
                borderTop: '1px solid rgba(255, 255, 255, 0.02)',
                paddingTop: '16px',
              }}>
                Rejections loop the briefs back to Synthesis with revision flags. Max 3 iterations.
              </div>
            </div>

          </div>

        </div>
      )}

    </div>
  );
}
