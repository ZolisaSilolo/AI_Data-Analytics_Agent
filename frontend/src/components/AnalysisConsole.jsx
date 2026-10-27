import React, { useState } from 'react';
import { Play, Sparkles, Compass, AlertCircle, Loader2 } from 'lucide-react';

const SUGGESTED_PROMPTS = {
  'General Exploratory': 'Identify key statistical distributions, correlation outliers, and anomalies across this dataset.',
  'Product Analytics': 'Analyze user cohort retention rates and identify stages in the funnel with the highest drop-off rate.',
  'Financial & RevOps': 'Reconcile the ARR waterfall, calculate Net Revenue Retention (NRR), and detect burn rate anomalies.',
  'Operations & Supply Chain': 'Apply Little\'s Law to calculate WIP, evaluate lead-time variance, and identify SLA breach risks.',
  'Marketing & Growth': 'Calculate attribution models across channels, assess CAC payback periods, and evaluate LTV:CAC ratios.',
  'Clinical & Biotech': 'Construct a 2x2 contingency table, compute the Odds Ratio with 95% confidence intervals, and run Fisher\'s exact test.'
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

  const handleDisciplineChange = (disc) => {
    setSelectedDiscipline(disc);
    if (SUGGESTED_PROMPTS[disc]) {
      setQuery(SUGGESTED_PROMPTS[disc]);
    }
  };

  const handleRunAnalysis = async () => {
    if (!query) {
      onError('Please enter an analytical question.');
      return;
    }
    if (!apiEndpoint) {
      onError('Please configure your AWS API Gateway endpoint in the settings.');
      return;
    }

    setIsAnalyzing(true);
    try {
      const payload = {
        query: query,
        discipline: selectedDiscipline,
        model_id: selectedModel,
        dataset_path: dataset?.name?.includes('/') ? dataset.name : 'datasets/my_data.parquet',
        generate_chart: true
      };

      const res = await fetch(`${apiEndpoint}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      if (res.ok && data.status === 'SUCCESS') {
        onAnalysisResult(data);
      } else {
        onError(data.error || 'Analysis execution failed.');
      }
    } catch (err) {
      onError(`Request error: ${err.message}`);
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
        />
      </div>

      <button
        className="btn-primary"
        onClick={handleRunAnalysis}
        disabled={isAnalyzing}
        style={{ width: '100%' }}
      >
        {isAnalyzing ? (
          <>
            <Loader2 size={16} className="animate-spin" />
            Compiling DuckDB SQL & Bedrock Agent...
          </>
        ) : (
          <>
            <Sparkles size={16} />
            Run Deterministic Analysis
          </>
        )}
      </button>
    </div>
  );
}
