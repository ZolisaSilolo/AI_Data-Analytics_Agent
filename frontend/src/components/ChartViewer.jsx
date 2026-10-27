import React, { useEffect, useRef } from 'react';
import { BarChart3 } from 'lucide-react';

export default function ChartViewer({ chartSpec }) {
  const chartRef = useRef(null);

  useEffect(() => {
    if (chartRef.current && window.Plotly && chartSpec) {
      const layout = {
        ...chartSpec.layout,
        autosize: true,
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        font: { color: '#94a3b8', family: 'Inter, sans-serif' },
        margin: { l: 50, r: 30, t: 40, b: 50 }
      };
      window.Plotly.newPlot(chartRef.current, chartSpec.data, layout, { responsive: true });
    }
  }, [chartSpec]);

  return (
    <div className="card">
      <div className="card-title">
        <BarChart3 size={16} color="#38bdf8" /> Declarative Visual Analysis
      </div>

      {chartSpec ? (
        <div ref={chartRef} style={{ width: '100%', minHeight: '360px' }} />
      ) : (
        <div style={{
          minHeight: '220px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--text-muted)',
          fontSize: '13px'
        }}>
          No active chart generated yet. Run an analysis with chart generation enabled.
        </div>
      )}
    </div>
  );
}
