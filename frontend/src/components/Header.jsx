import React, { useState } from 'react';
import { Cpu, Zap, Settings, ShieldCheck } from 'lucide-react';

export default function Header({
  apiEndpoint,
  setApiEndpoint,
  selectedModel,
  setSelectedModel
}) {
  const [showSettings, setShowSettings] = useState(false);

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

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Cpu size={14} color="#38bdf8" />
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            style={{ width: 'auto', padding: '4px 8px', fontSize: '12px', background: 'var(--bg-input)' }}
          >
            <option value="anthropic.claude-3-5-sonnet-20241022-v2:0">Claude 3.5 Sonnet</option>
            <option value="amazon.nova-pro-v1:0">Amazon Nova Pro</option>
            <option value="amazon.nova-lite-v1:0">Amazon Nova Lite</option>
          </select>
        </div>

        <button
          className="btn-secondary"
          onClick={() => setShowSettings(!showSettings)}
          style={{ padding: '6px 10px', fontSize: '12px' }}
          title="Configure API Gateway Endpoint"
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
          <label>AWS API Gateway Base URL:</label>
          <input
            type="text"
            value={apiEndpoint}
            onChange={(e) => setApiEndpoint(e.target.value)}
            placeholder="https://xxx.execute-api.us-east-1.amazonaws.com/dev"
          />
          <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '8px' }}>
            Set to your deployed AWS SAM HTTP API endpoint or local proxy.
          </p>
          <button
            className="btn-primary"
            style={{ marginTop: '12px', width: '100%' }}
            onClick={() => setShowSettings(false)}
          >
            Save Endpoint
          </button>
        </div>
      )}
    </header>
  );
}
