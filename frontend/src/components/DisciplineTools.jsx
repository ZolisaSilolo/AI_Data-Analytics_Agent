import React, { useState } from 'react';
import { Calculator, ArrowRight } from 'lucide-react';

export default function DisciplineTools({ selectedDiscipline }) {
  // Financial State
  const [begArr, setBegArr] = useState(1000000);
  const [newArr, setNewArr] = useState(250000);
  const [expArr, setExpArr] = useState(150000);
  const [contArr, setContArr] = useState(30000);
  const [churnArr, setChurnArr] = useState(70000);
  const [finResult, setFinResult] = useState(null);

  // Operations State
  const [throughput, setThroughput] = useState(15);
  const [cycleTime, setCycleTime] = useState(4.5);
  const [opsResult, setOpsResult] = useState(null);

  // Clinical State
  const [expCases, setExpCases] = useState(25);
  const [expNon, setExpNon] = useState(75);
  const [unexpCases, setUnexpCases] = useState(10);
  const [unexpNon, setUnexpNon] = useState(90);
  const [clinResult, setClinResult] = useState(null);

  const calculateFinancial = () => {
    const net = newArr + expArr - contArr - churnArr;
    const ending = begArr + net;
    const nrr = begArr > 0 ? (begArr + expArr - contArr - churnArr) / begArr : 0;
    const grr = begArr > 0 ? (begArr - contArr - churnArr) / begArr : 0;
    setFinResult({ net, ending, nrr: (nrr * 100).toFixed(1), grr: (grr * 100).toFixed(1) });
  };

  const calculateOperations = () => {
    const wip = throughput * cycleTime;
    setOpsResult({ wip: wip.toFixed(2) });
  };

  const calculateClinical = () => {
    const orVal = (expCases * unexpNon) / Math.max(1, (expNon * unexpCases));
    const riskExp = expCases / (expCases + expNon);
    const riskUnexp = unexpCases / (unexpCases + unexpNon);
    const rrVal = riskExp / Math.max(0.0001, riskUnexp);
    setClinResult({ oddsRatio: orVal.toFixed(3), relativeRisk: rrVal.toFixed(3) });
  };

  return (
    <div className="card">
      <div className="card-title">
        <Calculator size={16} color="#38bdf8" /> Specialized {selectedDiscipline} Tool
      </div>

      {selectedDiscipline === 'Financial & RevOps' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '8px' }}>
            <div>
              <label>Beginning ARR</label>
              <input type="number" value={begArr} onChange={e => setBegArr(+e.target.value)} />
            </div>
            <div>
              <label>New ARR</label>
              <input type="number" value={newArr} onChange={e => setNewArr(+e.target.value)} />
            </div>
            <div>
              <label>Expansion</label>
              <input type="number" value={expArr} onChange={e => setExpArr(+e.target.value)} />
            </div>
            <div>
              <label>Contraction</label>
              <input type="number" value={contArr} onChange={e => setContArr(+e.target.value)} />
            </div>
            <div>
              <label>Churn</label>
              <input type="number" value={churnArr} onChange={e => setChurnArr(+e.target.value)} />
            </div>
          </div>
          <button className="btn-secondary" onClick={calculateFinancial}>
            Compute ARR Waterfall & NRR
          </button>
          <p className="local-note">
            Local arithmetic for quick what-ifs. Dataset-backed figures come from the sandboxed SQL engine.
          </p>
          {finResult && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', marginTop: '6px' }}>
              <div className="metric-card">
                <span>Net ARR Change</span>
                <h3 style={{ color: finResult.net >= 0 ? '#34d399' : '#ef4444' }}>${finResult.net.toLocaleString()}</h3>
              </div>
              <div className="metric-card">
                <span>Ending ARR</span>
                <h3>${finResult.ending.toLocaleString()}</h3>
              </div>
              <div className="metric-card">
                <span>NRR</span>
                <h3>{finResult.nrr}%</h3>
              </div>
              <div className="metric-card">
                <span>GRR</span>
                <h3>{finResult.grr}%</h3>
              </div>
            </div>
          )}
        </div>
      )}

      {selectedDiscipline === 'Operations & Supply Chain' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label>Throughput Rate (λ units/hr)</label>
              <input type="number" value={throughput} onChange={e => setThroughput(+e.target.value)} />
            </div>
            <div>
              <label>Cycle Time (W hours)</label>
              <input type="number" value={cycleTime} onChange={e => setCycleTime(+e.target.value)} />
            </div>
          </div>
          <button className="btn-secondary" onClick={calculateOperations}>Compute Little's Law</button>
          <p className="local-note">
            Local arithmetic for quick what-ifs. Dataset-backed figures come from the sandboxed SQL engine.
          </p>
          {opsResult && (
            <div className="metric-card" style={{ marginTop: '6px' }}>
              <span>Work In Progress (WIP = λ × W)</span>
              <h3>{opsResult.wip} units</h3>
            </div>
          )}
        </div>
      )}

      {selectedDiscipline === 'Clinical & Biotech' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px' }}>
            <div>
              <label>Exposed Cases</label>
              <input type="number" value={expCases} onChange={e => setExpCases(+e.target.value)} />
            </div>
            <div>
              <label>Exposed Non-Cases</label>
              <input type="number" value={expNon} onChange={e => setExpNon(+e.target.value)} />
            </div>
            <div>
              <label>Unexposed Cases</label>
              <input type="number" value={unexpCases} onChange={e => setUnexpCases(+e.target.value)} />
            </div>
            <div>
              <label>Unexposed Non-Cases</label>
              <input type="number" value={unexpNon} onChange={e => setUnexpNon(+e.target.value)} />
            </div>
          </div>
          <button className="btn-secondary" onClick={calculateClinical}>Calculate Odds Ratio & RR</button>
          <p className="local-note">
            Local arithmetic for quick what-ifs. Dataset-backed figures come from the sandboxed SQL engine.
          </p>
          {clinResult && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginTop: '6px' }}>
              <div className="metric-card">
                <span>Odds Ratio (OR)</span>
                <h3>{clinResult.oddsRatio}</h3>
              </div>
              <div className="metric-card">
                <span>Relative Risk (RR)</span>
                <h3>{clinResult.relativeRisk}</h3>
              </div>
            </div>
          )}
        </div>
      )}

      {selectedDiscipline !== 'Financial & RevOps' &&
       selectedDiscipline !== 'Operations & Supply Chain' &&
       selectedDiscipline !== 'Clinical & Biotech' && (
        <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
          Discipline engine active. The model computes dataset-backed metrics with the
          sandboxed SQL engine; no analysis code runs in your browser.
        </p>
      )}
    </div>
  );
}
