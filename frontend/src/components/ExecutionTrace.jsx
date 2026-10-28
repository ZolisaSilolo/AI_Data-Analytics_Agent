import React from 'react';
import { Terminal, ShieldCheck, Clock, CheckCircle, AlertTriangle } from 'lucide-react';

export default function ExecutionTrace({ toolExecutions, executionTimeSeconds }) {
  if (!toolExecutions || toolExecutions.length === 0) {
    return (
      <div className="card">
        <div className="card-title">
          <Terminal size={16} color="#38bdf8" /> Execution Audit Trace
        </div>
        <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
          No tools executed for this round.
        </p>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-title" style={{ justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Terminal size={16} color="#38bdf8" /> Compiled Execution Audit Trail
        </div>
        {executionTimeSeconds && (
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Clock size={12} /> {executionTimeSeconds}s total runtime
          </span>
        )}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
        {toolExecutions.map((t, idx) => {
          const invariants = t.output?.invariants;
          return (
            <div
              key={idx}
              style={{
                border: '1px solid var(--border)',
                borderRadius: '8px',
                padding: '14px',
                background: 'rgba(15, 23, 42, 0.6)'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontSize: '12px', fontWeight: 600, color: '#38bdf8' }}>
                  Step {idx + 1}: Tool <code>{t.tool}</code>
                </span>
                {t.output?.execution_time_ms !== undefined && (
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    Engine: {t.output?.engine || 'duckdb'} • {t.output?.execution_time_ms} ms
                  </span>
                )}
              </div>

              {/* SQL input (the only executable artifact the model produces) */}
              {t.input?.sql && (
                <div style={{ marginBottom: '8px' }}>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px' }}>Compiled SQL:</div>
                  <pre className="code-box">{t.input.sql}</pre>
                </div>
              )}

              {/* Invariant Verification Gates */}
              {invariants && (
                <div style={{ marginTop: '10px', paddingTop: '10px', borderTop: '1px solid rgba(51, 65, 85, 0.4)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', fontWeight: 600, marginBottom: '6px' }}>
                    <ShieldCheck size={13} color={invariants.all_passed ? '#10b981' : '#f59e0b'} />
                    Invariant Verification Gates:
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                    {invariants.checks?.map((chk, cIdx) => (
                      <span
                        key={cIdx}
                        style={{
                          fontSize: '10px',
                          padding: '2px 8px',
                          borderRadius: '4px',
                          background: chk.passed ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                          color: chk.passed ? '#34d399' : '#fbbf24',
                          border: `1px solid ${chk.passed ? 'rgba(16, 185, 129, 0.3)' : 'rgba(245, 158, 11, 0.3)'}`
                        }}
                      >
                        {chk.passed ? '✓' : '⚠'} {chk.name}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
