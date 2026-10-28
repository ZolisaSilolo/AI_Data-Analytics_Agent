import React, { useEffect, useRef, useState } from 'react';
import { BarChart3 } from 'lucide-react';

/**
 * Plotly is ~4.6 MB, so it is loaded on demand rather than shipped in the
 * initial bundle. The first chart render pays the download; the rest is cached.
 */
export default function ChartViewer({ chartSpec }) {
  const chartRef = useRef(null);
  const [loadError, setLoadError] = useState(null);

  useEffect(() => {
    const node = chartRef.current;
    if (!node || !chartSpec) return undefined;

    let cancelled = false;
    let plotlyModule = null;

    (async () => {
      try {
        const mod = await import('plotly.js-dist-min');
        if (cancelled) return;
        plotlyModule = mod.default || mod;

        const layout = {
          ...chartSpec.layout,
          autosize: true,
          paper_bgcolor: 'transparent',
          plot_bgcolor: 'transparent',
          font: { color: '#94a3b8', family: 'Inter, sans-serif' },
          margin: { l: 50, r: 30, t: 40, b: 50 }
        };
        plotlyModule.react(node, chartSpec.data, layout, {
          responsive: true,
          displayModeBar: false
        });
      } catch {
        if (!cancelled) setLoadError('The charting library could not be loaded.');
      }
    })();

    return () => {
      cancelled = true;
      if (plotlyModule) plotlyModule.purge(node);
    };
  }, [chartSpec]);

  return (
    <div className="card">
      <div className="card-title">
        <BarChart3 size={16} color="#38bdf8" /> Declarative Visual Analysis
      </div>

      {loadError && (
        <p style={{ fontSize: '12px', color: '#f87171' }}>{loadError}</p>
      )}

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
          No active chart yet. Run an analysis that returns a table.
        </div>
      )}
    </div>
  );
}
