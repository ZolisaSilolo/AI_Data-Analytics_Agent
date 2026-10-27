import React, { useState } from 'react';
import Header from './components/Header.jsx';
import DataIngestion from './components/DataIngestion.jsx';
import AnalysisConsole from './components/AnalysisConsole.jsx';
import ExecutionTrace from './components/ExecutionTrace.jsx';
import ChartViewer from './components/ChartViewer.jsx';
import DisciplineTools from './components/DisciplineTools.jsx';
import { Table, CheckCircle2, AlertCircle } from 'lucide-react';

export default function App() {
  const [apiEndpoint, setApiEndpoint] = useState(
    import.meta.env.VITE_API_ENDPOINT || 'https://api.execute-api.us-east-1.amazonaws.com/dev'
  );
  const [selectedModel, setSelectedModel] = useState('anthropic.claude-3-5-sonnet-20241022-v2:0');
  const [selectedDiscipline, setSelectedDiscipline] = useState('General Exploratory');
  const [dataset, setDataset] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [activeTab, setActiveTab] = useState('report'); // 'report' | 'trace' | 'chart' | 'preview'
  const [toast, setToast] = useState(null);

  const showToast = (message, isError = false) => {
    setToast({ message, isError });
    setTimeout(() => setToast(null), 4500);
  };

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
          {/* Top Metrics Row */}
          {dataset && (
            <div className="metrics-grid">
              <div className="metric-card">
                <span>Total Rows</span>
                <h3>{dataset.rowCount?.toLocaleString() || 0}</h3>
              </div>
              <div className="metric-card">
                <span>Columns</span>
                <h3>{dataset.headers?.length || 0}</h3>
              </div>
              <div className="metric-card">
                <span>Active Model</span>
                <h3 style={{ fontSize: '14px', marginTop: '8px' }}>
                  {selectedModel.includes('claude') ? 'Claude 3.5 Sonnet' : 'Amazon Nova Pro'}
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
                <div style={{ fontSize: '13px', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                  {analysisResult.analysis}
                </div>
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
              <div className="card-title">Dataset Sample Preview</div>
              {dataset?.sampleRows && dataset.sampleRows.length > 0 ? (
                <div className="table-wrapper">
                  <table>
                    <thead>
                      <tr>
                        {dataset.headers?.map((h, i) => (
                          <th key={i}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {dataset.sampleRows.slice(0, 20).map((row, rIdx) => (
                        <tr key={rIdx}>
                          {dataset.headers?.map((h, cIdx) => (
                            <td key={cIdx}>{row[h] !== null ? String(row[h]) : '-'}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                  Upload a dataset or extract tables from a web URL to preview records.
                </p>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
