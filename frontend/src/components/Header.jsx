import React, { useState } from 'react';
import { Cpu, Zap, Settings, ShieldCheck } from 'lucide-react';

export default function Header({
  apiEndpoint,
  setApiEndpoint,
  selectedModel,
  setSelectedModel
}) {
  const [showSettings, setShowSettings] = useState(false);
  const [draftEndpoint, setDraftEndpoint] = useState(apiEndpoint || '');
  const editable = import.meta.env.DEV;

  const saveEndpoint = () => {
    const value = draftEndpoint.trim().replace(/\/+$/, '');
    setApiEndpoint(value);
    try {
      if (value) localStorage.setItem('omni.apiEndpoint', value);
      else localStorage.removeItem('omni.apiEndpoint');
    } catch {
      /* storage may be unavailable in private mode */
    }
    setShowSettings(false);
  };

  return (
    <header>
      <div className="brand">
        <span className="brand-icon">🦁</span>
        <div>
          <h1>OmniAnalyst</h1>
          <p style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            Deterministic Data Analyst Platform
          </p>
        </div>
      </div>

      <div className="header-badges">
        <span className="badge badge-serverless">
          <Zap size={13} /> Scale-to-Zero
        </span>

        <span className="badge" title="SQL is statically validated and executed in an isolated read-only sandbox">
          <ShieldCheck size={13} /> Read-only sandbox
        </span>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Cpu size={14} color="#38bdf8" />
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            style={{ width: 'auto', padding: '4px 8px', fontSize: '12px', background: 'var(--bg-input)' }}
          >
            <option value="global.moonshotai.kimi-k3">Kimi K3 (global)</option>
            <option value="global.anthropic.claude-sonnet-4-5-20250929-v1:0">
              Claude Sonnet 4.5 (needs approval)
            </option>
          </select>
        </div>

        <button
          className="btn-secondary"
          onClick={() => {
            setDraftEndpoint(apiEndpoint || '');
            setShowSettings((open) => !open);
          }}
          style={{ padding: '6px 10px', fontSize: '12px' }}
          title="API endpoint settings"
        >
          <Settings size={14} /> API
        </button>
      </div>

      {showSettings && (
        <div style={{
          position: 'absolute',
          top: '60px',
          right: '28px',
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: '8px',
          padding: '16px',
          width: '360px',
          zIndex: 100,
          boxShadow: '0 10px 25px rgba(0,0,0,0.5)'
        }}>
          <label>API Gateway Base URL:</label>
          <input
            type="text"
            value={draftEndpoint}
            onChange={(e) => setDraftEndpoint(e.target.value)}
            placeholder="https://<api-id>.execute-api.<region>.amazonaws.com/dev"
            readOnly={!editable}
          />
          <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '8px' }}>
            {editable
              ? 'Development only: override the locally configured endpoint.'
              : 'Configured at build time via VITE_API_ENDPOINT.'}
          </p>
          {editable && (
            <button
              className="btn-primary"
              style={{ marginTop: '12px', width: '100%' }}
              onClick={saveEndpoint}
            >
              Save Endpoint
            </button>
          )}
        </div>
      )}
    </header>
  );
}
