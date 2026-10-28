import React, { useEffect, useRef, useState } from 'react';
import { Play, Sparkles, Compass, Loader2, Clock, XCircle, CheckCircle2 } from 'lucide-react';
import { analyze, pollJob, ApiError } from '../lib/api.js';

const SUGGESTED_PROMPTS = {
  'General Exploratory': 'Identify key statistical distributions, correlation outliers, and anomalies across this dataset.',
  'Product Analytics': 'Analyze user cohort retention rates and identify stages in the funnel with the highest drop-off rate.',
  'Financial & RevOps': 'Reconcile the ARR waterfall, calculate Net Revenue Retention (NRR), and detect burn rate anomalies.',
  'Operations & Supply Chain': 'Apply Little\'s Law to calculate WIP, evaluate lead-time variance, and identify SLA breach risks.',
  'Marketing & Growth': 'Calculate attribution models across channels, assess CAC payback periods, and evaluate LTV:CAC ratios.',
  'Clinical & Biotech': 'Construct a 2x2 contingency table, compute the Odds Ratio with 95% confidence intervals, and run Fisher\'s exact test.'
};

const STATUS_LABEL = {
  QUEUED: 'Queued — waiting for a worker',
  RUNNING: 'Running — compiling SQL and executing deterministically',
  RETRYING: 'Retrying — the previous attempt failed transiently',
  COMPLETED: 'Completed',
  FAILED: 'Failed'
};

export default function AnalysisConsole({
  selectedDiscipline,
  setSelectedDiscipline,
  dataset,
  apiEndpoint,
  selectedModel,
  onAnalysisResult,
  onError
}) {
  const [query, setQuery] = useState(SUGGESTED_PROMPTS['General Exploratory']);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [jobStatus, setJobStatus] = useState(null);
  const [elapsed, setElapsed] = useState(0);
  const abortRef = useRef(null);

  useEffect(() => () => abortRef.current?.abort(), []);

  useEffect(() => {
    if (!isAnalyzing) return undefined;
    const started = Date.now();
    const timer = setInterval(() => setElapsed(Math.round((Date.now() - started) / 1000)), 1000);
    return () => clearInterval(timer);
  }, [isAnalyzing]);

  const handleDisciplineChange = (discipline) => {
    setSelectedDiscipline(discipline);
    if (SUGGESTED_PROMPTS[discipline]) setQuery(SUGGESTED_PROMPTS[discipline]);
  };

  const stopPolling = () => {
    abortRef.current?.abort();
    setIsAnalyzing(false);
    setJobStatus(null);
  };

  const handleRunAnalysis = async () => {
    if (!query.trim()) {
      onError('Please enter an analytical question.');
      return;
    }
    if (!apiEndpoint) {
      onError('Configure the API endpoint in settings first.');
      return;
    }
    if (!dataset?.key) {
      onError('Upload or attach a dataset before running an analysis.');
      return;
    }

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setIsAnalyzing(true);
    setElapsed(0);
    setJobStatus('QUEUED');

    try {
      const submitted = await analyze(
        apiEndpoint,
        {
          query: query.trim(),
          dataset_key: dataset.key,
          discipline: selectedDiscipline,
          model_id: selectedModel,
          generate_chart: true
        },
        { signal: controller.signal }
      );

      setJobStatus('QUEUED');
      const job = await pollJob(apiEndpoint, submitted.job_id, {
        signal: controller.signal,
        onTick: (tick) => setJobStatus(tick.status)
      });

      setJobStatus('COMPLETED');
      onAnalysisResult({ ...job.result, job_id: job.job_id });
    } catch (err) {
      if (err.name === 'AbortError') return;
      setJobStatus('FAILED');
      onError(err instanceof ApiError ? err.message : 'Analysis failed.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="card">
      <div className="card-title">
        <Compass size={16} color="#38bdf8" /> Analytical Discipline & Console
      </div>

      <div style={{ marginBottom: '14px' }}>
        <label>Select Discipline Engine:</label>
        <select
          value={selectedDiscipline}
          onChange={(e) => handleDisciplineChange(e.target.value)}
          disabled={isAnalyzing}
        >
          <option value="General Exploratory">General Exploratory</option>
          <option value="Product Analytics">Product Analytics (Funnels, Retention)</option>
          <option value="Financial & RevOps">Financial & RevOps (ARR, NRR, Runway)</option>
          <option value="Operations & Supply Chain">Operations & Supply Chain (Little's Law, SLA)</option>
          <option value="Marketing & Growth">Marketing & Growth (Attribution, CAC/LTV)</option>
          <option value="Clinical & Biotech">Clinical & Biotech (Fisher's Exact, Odds Ratio)</option>
        </select>
      </div>

      <div style={{ marginBottom: '14px' }}>
        <label>Formulate Hypothesis or Business Query:</label>
        <textarea
          rows={3}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask a question..."
          disabled={isAnalyzing}
        />
      </div>

      <button
        className="btn-primary"
        onClick={handleRunAnalysis}
        disabled={isAnalyzing || !dataset?.key}
        style={{ width: '100%' }}
      >
        {isAnalyzing ? (
          <>
            <Loader2 size={16} className="animate-spin" />
            {STATUS_LABEL[jobStatus] || 'Working...'}
          </>
        ) : (
          <>
            <Sparkles size={16} />
            Run Deterministic Analysis
          </>
        )}
      </button>

      {isAnalyzing && (
        <div style={{
          marginTop: '12px',
          padding: '10px 12px',
          background: 'var(--bg-input)',
          border: '1px solid var(--border)',
          borderRadius: '6px',
          fontSize: '11px',
          color: 'var(--text-muted)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Clock size={12} /> {elapsed}s elapsed • job runs server-side, safe to leave this tab open
            </span>
            <button
              className="btn-secondary"
              style={{ padding: '2px 8px', fontSize: '10px' }}
              onClick={stopPolling}
              title="Stop polling. The server-side job continues."
            >
              <XCircle size={11} /> Stop polling
            </button>
          </div>
        </div>
      )}

      {!isAnalyzing && jobStatus === 'COMPLETED' && (
        <div style={{ marginTop: '10px', fontSize: '11px', color: '#34d399', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <CheckCircle2 size={12} /> Analysis completed and verified.
        </div>
      )}
    </div>
  );
}
