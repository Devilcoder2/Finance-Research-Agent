import React, { useState } from 'react';
import { Eye, EyeOff, Lock, Mail, ShieldAlert } from 'lucide-react';
import { DEFAULT_USER, STORAGE_KEYS } from '../constants';

interface LoginProps {
  onLoginSuccess: (user: typeof DEFAULT_USER) => void;
}

export function Login({ onLoginSuccess }: LoginProps) {
  const [email, setEmail] = useState('analyst@example.com');
  const [password, setPassword] = useState('••••••••••••');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    // Simulate database lookup and JWT authentication
    setTimeout(() => {
      if (email === 'analyst@example.com') {
        localStorage.setItem(STORAGE_KEYS.AUTH_TOKEN, 'mock_jwt_token_analyst');
        localStorage.setItem(STORAGE_KEYS.USER_INFO, JSON.stringify(DEFAULT_USER));
        onLoginSuccess(DEFAULT_USER);
      } else {
        setError('Invalid credentials. Please use the default seeded analyst account.');
      }
      setLoading(false);
    }, 800);
  };

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      padding: '24px',
    }}>
      <div className="glass-panel animate-fade-in" style={{
        width: '100%',
        maxWidth: '440px',
        padding: '40px',
        position: 'relative',
        overflow: 'hidden',
      }}>
        {/* Glow Effects */}
        <div style={{
          position: 'absolute',
          top: '-15%',
          right: '-15%',
          width: '180px',
          height: '180px',
          background: 'radial-gradient(circle, rgba(139, 92, 246, 0.2) 0%, transparent 70%)',
          borderRadius: '50%',
          filter: 'blur(10px)',
        }} />

        <div style={{ textAlign: 'center', marginBottom: '36px' }}>
          <h1 className="font-display text-gradient-purple-cyan" style={{
            fontSize: '32px',
            fontWeight: 800,
            marginBottom: '8px',
          }}>
            Antigravity Finance
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>
            Hierarchical Multi-Agent Research Platform
          </p>
        </div>

        {error && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.2)',
            borderRadius: 'var(--border-radius-sm)',
            padding: '12px 16px',
            marginBottom: '24px',
            color: 'var(--accent-danger)',
            fontSize: '13px',
          }}>
            <ShieldAlert size={18} style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <label htmlFor="email" style={{
              color: 'var(--text-bright)',
              fontSize: '13px',
              fontWeight: 500,
            }}>
              Analyst Email Address
            </label>
            <div style={{ position: 'relative' }}>
              <Mail size={18} style={{
                position: 'absolute',
                left: '16px',
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'var(--text-muted)',
              }} />
              <input
                id="email"
                type="email"
                className="glass-input"
                style={{ width: '100%', paddingLeft: '48px' }}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={loading}
              />
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label htmlFor="password" style={{
                color: 'var(--text-bright)',
                fontSize: '13px',
                fontWeight: 500,
              }}>
                Security Key / Password
              </label>
            </div>
            <div style={{ position: 'relative' }}>
              <Lock size={18} style={{
                position: 'absolute',
                left: '16px',
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'var(--text-muted)',
              }} />
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                className="glass-input"
                style={{ width: '100%', paddingLeft: '48px', paddingRight: '48px' }}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={loading}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={{
                  position: 'absolute',
                  right: '16px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                }}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            className="btn-premium animate-glow-purple"
            style={{ width: '100%', marginTop: '8px' }}
            disabled={loading}
          >
            {loading ? 'Authenticating Analyst...' : 'Sign In To Terminal'}
          </button>
        </form>

        <div style={{
          marginTop: '32px',
          textAlign: 'center',
          fontSize: '12px',
          color: 'var(--text-dark)',
          borderTop: '1px solid rgba(255, 255, 255, 0.03)',
          paddingTop: '20px',
        }}>
          Authorized analyst access only. Security logs active.
        </div>
      </div>
    </div>
  );
}
