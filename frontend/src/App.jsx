import React, { useState } from 'react';
import Header from './components/Header.jsx';
import DataIngestion from './components/DataIngestion.jsx';
import AnalysisConsole from './components/AnalysisConsole.jsx';
import ExecutionTrace from './components/ExecutionTrace.jsx';
import ChartViewer from './components/ChartViewer.jsx';
import DisciplineTools from './components/DisciplineTools.jsx';
import { AlertCircle, CheckCircle2 } from 'lucide-react';

function readStoredEndpoint() {
  try {
    return localStorage.getItem('omni.apiEndpoint') || '';
  } catch {
    return '';
  }
}

export default function App() {
  const [apiEndpoint, setApiEndpointState] = useState(
    import.meta.env.VITE_API_ENDPOINT || readStoredEndpoint()
  );
  const setApiEndpoint = (value) => setApiEndpointState(value);
  const [selectedModel, setSelectedModel] = useState('global.moonshotai.kimi-k3');
  const [selectedDiscipline, setSelectedDiscipline] = useState('General Exploratory');
  const [dataset, setDataset] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [activeTab, setActiveTab] = useState('report'); // 'report' | 'trace' | 'chart' | 'preview'
  const [toast, setToast] = useState(null);

  const showToast = (message, isError = false) => {
    setToast({ message, isError });
    setTimeout(() => setToast(null), 4500);
  };

  // The API now returns a real profile; prefer it over the upload placeholder.
  const displayRows = dataset?.rowCount ?? analysisResult?.dataset?.row_count ?? null;
  const displayCols = dataset?.headers?.length ?? analysisResult?.dataset?.columns?.length ?? null;
  const verification = analysisResult?.verification;
  const warnings = analysisResult?.warnings || [];

  return (
    <div className="app-container">
      <Header
        apiEndpoint={apiEndpoint}
        setApiEndpoint={setApiEndpoint}
        selectedModel={selectedModel}
        setSelectedModel={setSelectedModel}
      />

      {toast && (
        <div style={{
          position: 'fixed',
          top: '70px',
          right: '24px',
          background: toast.isError ? '#7f1d1d' : '#064e3b',
          color: '#fff',
          padding: '10px 16px',
          borderRadius: '6px',
          fontSize: '12px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          zIndex: 1000,
          border: `1px solid ${toast.isError ? '#ef4444' : '#10b981'}`
        }}>
          {toast.isError ? <AlertCircle size={16} /> : <CheckCircle2 size={16} />}
          {toast.message}
        </div>
      )}

      <div className="main-layout">
        <aside className="sidebar">
          <DataIngestion
            dataset={dataset}
            setDataset={setDataset}
            apiEndpoint={apiEndpoint}
            onError={(msg) => showToast(msg, true)}
            onSuccess={(msg) => showToast(msg, false)}
          />

          <DisciplineTools selectedDiscipline={selectedDiscipline} />
        </aside>

        <main className="content">
          {!apiEndpoint && (
            <div className="card" style={{ borderColor: '#f59e0b', marginBottom: '16px' }}>
              <div className="card-title" style={{ color: '#fbbf24' }}>
                <AlertCircle size={16} /> API endpoint not configured
              </div>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                Set <code>VITE_API_ENDPOINT</code> at build time (Amplify environment variable) or
                open the API settings in development.
              </p>
            </div>
          )}

          {/* Top Metrics Row */}
          {dataset && (
            <div className="metrics-grid">
              <div className="metric-card">
                <span>Total Rows</span>
                <h3>{displayRows != null ? displayRows.toLocaleString() : '—'}</h3>
              </div>
              <div className="metric-card">
                <span>Columns</span>
                <h3>{displayCols ?? '—'}</h3>
              </div>
              <div className="metric-card">
                <span>Active Model</span>
                <h3 style={{ fontSize: '14px', marginTop: '8px' }}>
                  {selectedModel.includes('claude')
                    ? 'Claude Sonnet 4.5'
                    : selectedModel.includes('moonshot')
                      ? 'Kimi K3'
                      : 'Amazon Nova Pro'}
                </h3>
              </div>
              <div className="metric-card">
                <span>Engine</span>
                <h3>DuckDB + Bedrock</h3>
              </div>
            </div>
          )}

          <AnalysisConsole
            selectedDiscipline={selectedDiscipline}
            setSelectedDiscipline={setSelectedDiscipline}
            dataset={dataset}
            apiEndpoint={apiEndpoint}
            selectedModel={selectedModel}
            onAnalysisResult={(res) => {
              setAnalysisResult(res);
              showToast('Analysis completed successfully!');
            }}
            onError={(msg) => showToast(msg, true)}
          />

          {/* Navigation Tabs */}
          <div className="tabs">
            <button
              className={`tab-btn ${activeTab === 'report' ? 'active' : ''}`}
              onClick={() => setActiveTab('report')}
            >
              📋 Executive Report
            </button>
            <button
              className={`tab-btn ${activeTab === 'trace' ? 'active' : ''}`}
              onClick={() => setActiveTab('trace')}
            >
              🔍 Execution Trace
            </button>
            <button
              className={`tab-btn ${activeTab === 'chart' ? 'active' : ''}`}
              onClick={() => setActiveTab('chart')}
            >
              📊 Visual Analysis
            </button>
            <button
              className={`tab-btn ${activeTab === 'preview' ? 'active' : ''}`}
              onClick={() => setActiveTab('preview')}
            >
              📄 Data Preview
            </button>
          </div>

          {/* Tab 1: Executive Report */}
          {activeTab === 'report' && (
            <div className="card">
              <div className="card-title">Executive Analytical Synthesis</div>
              {analysisResult ? (
                <>
                  <div style={{ fontSize: '13px', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                    {analysisResult.analysis}
                  </div>

                  {verification && (
                    <div style={{
                      marginTop: '14px',
                      padding: '8px 12px',
                      borderRadius: '6px',
                      fontSize: '11px',
                      border: `1px solid ${verification.status === 'PASS' ? '#065f46' : '#7f1d1d'}`,
                      background: verification.status === 'PASS' ? '#022c22' : '#2a0a0a',
                      color: verification.status === 'PASS' ? '#34d399' : '#fca5a5',
                    }}>
                      {verification.status === 'PASS'
                        ? `✓ Evidence check: ${verification.supported}/${verification.checked} numbers verified against tool outputs`
                        : verification.status === 'NO_CLAIMS'
                          ? 'Evidence check: narrative contains no numbers'
                          : `⚠ Evidence check: ${verification.unsupported_count} unsupported number(s) — review before sharing`}
                    </div>
                  )}

                  {warnings.map((warning, index) => (
                    <div key={index} style={{
                      marginTop: '8px',
                      fontSize: '11px',
                      color: '#fbbf24',
                    }}>
                      ⚠ {warning}
                    </div>
                  ))}
                </>
              ) : (
                <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                  Submit an analytical inquiry above to generate a synthesized executive report.
                </p>
              )}
            </div>
          )}

          {/* Tab 2: Execution Trace */}
          {activeTab === 'trace' && (
            <ExecutionTrace
              toolExecutions={analysisResult?.tool_executions}
              executionTimeSeconds={analysisResult?.execution_time_seconds}
            />
          )}

          {/* Tab 3: Chart Viewer */}
          {activeTab === 'chart' && (
            <ChartViewer chartSpec={analysisResult?.chart_spec} />
          )}

          {/* Tab 4: Data Preview */}
          {activeTab === 'preview' && (
            <div className="card">
              <div className="card-title">
                Dataset Sample Preview
              </div>
              {analysisResult?.dataset ? (
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.7 }}>
                  <div><strong style={{ color: 'var(--text-primary)' }}>Dataset:</strong> {analysisResult.dataset.key || 'browser-extracted table'}</div>
                  <div><strong style={{ color: 'var(--text-primary)' }}>Rows:</strong> {analysisResult.dataset.row_count?.toLocaleString()}</div>
                  <div><strong style={{ color: 'var(--text-primary)' }}>Columns:</strong> {analysisResult.dataset.columns?.join(', ')}</div>
                  <p style={{ marginTop: '10px' }}>
                    Row previews are not returned by the API to keep payloads small. Use the
                    Execution Trace tab to inspect the exact SQL and invariant checks.
                  </p>
                </div>
              ) : (
                <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                  Upload a dataset or extract tables with the browser extension, then run an
                  analysis to see its schema.
                </p>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
