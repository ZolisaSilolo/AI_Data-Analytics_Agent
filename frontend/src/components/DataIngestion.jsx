import React, { useState } from 'react';
import { Upload, Globe, Database, FileText, Loader2 } from 'lucide-react';

export default function DataIngestion({
  dataset,
  setDataset,
  apiEndpoint,
  onError,
  onSuccess
}) {
  const [ingestMode, setIngestMode] = useState('upload'); // 'upload' | 'playwright' | 's3'
  const [scrapeUrl, setScrapeUrl] = useState('');
  const [tableSelector, setTableSelector] = useState('table');
  const [s3Key, setS3Key] = useState('datasets/sample_data.parquet');
  const [isLoading, setIsLoading] = useState(false);

  // Parse local CSV file
  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const text = event.target.result;
        const lines = text.split('\n').filter(l => l.trim().length > 0);
        if (lines.length < 2) throw new Error('File must contain a header and at least one data row.');

        const headers = lines[0].split(',').map(h => h.trim().replace(/^["']|["']$/g, ''));
        const rows = lines.slice(1, 101).map(l => {
          const vals = l.split(',').map(v => v.trim().replace(/^["']|["']$/g, ''));
          const rowObj = {};
          headers.forEach((h, i) => {
            rowObj[h] = vals[i] !== undefined ? vals[i] : null;
          });
          return rowObj;
        });

        setDataset({
          name: file.name,
          headers,
          rowCount: lines.length - 1,
          sampleRows: rows
        });
        onSuccess(`Loaded ${file.name} (${lines.length - 1} rows)`);
      } catch (err) {
        onError(`CSV Parse Error: ${err.message}`);
      }
    };
    reader.readAsText(file);
  };

  // Trigger Playwright web scraper
  const handleWebScrape = async () => {
    if (!scrapeUrl) {
      onError('Please enter a target URL.');
      return;
    }
    setIsLoading(true);
    try {
      const response = await fetch(`${apiEndpoint}/browser/extract`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: scrapeUrl, table_selector: tableSelector })
      });
      const data = await response.json();
      if (data.status === 'SUCCESS' && data.tables && data.tables.length > 0) {
        const firstTable = data.tables[0];
        setDataset({
          name: data.page_title || scrapeUrl,
          headers: firstTable.columns,
          rowCount: firstTable.row_count,
          sampleRows: firstTable.sample_records
        });
        onSuccess(`Extracted ${firstTable.row_count} rows from ${data.page_title}!`);
      } else {
        onError(data.message || data.error || 'No tabular data extracted.');
      }
    } catch (err) {
      onError(`Playwright scrape failed: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="card">
      <div className="card-title">
        <Database size={16} color="#38bdf8" /> Data Ingestion
      </div>

      <div style={{ display: 'flex', gap: '6px', marginBottom: '16px' }}>
        <button
          className={`btn-secondary ${ingestMode === 'upload' ? 'active' : ''}`}
          style={{ flex: 1, padding: '6px 8px', fontSize: '11px' }}
          onClick={() => setIngestMode('upload')}
        >
          <Upload size={13} /> Upload
        </button>
        <button
          className={`btn-secondary ${ingestMode === 'playwright' ? 'active' : ''}`}
          style={{ flex: 1, padding: '6px 8px', fontSize: '11px' }}
          onClick={() => setIngestMode('playwright')}
        >
          <Globe size={13} /> Web Portal
        </button>
        <button
          className={`btn-secondary ${ingestMode === 's3' ? 'active' : ''}`}
          style={{ flex: 1, padding: '6px 8px', fontSize: '11px' }}
          onClick={() => setIngestMode('s3')}
        >
          <FileText size={13} /> S3 Key
        </button>
      </div>

      {ingestMode === 'upload' && (
        <div>
          <label>Choose CSV or Dataset File:</label>
          <input type="file" accept=".csv,.json" onChange={handleFileUpload} />
        </div>
      )}

      {ingestMode === 'playwright' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div>
            <label>Web Portal / Dashboard URL:</label>
            <input
              type="text"
              placeholder="https://example.com/analytics"
              value={scrapeUrl}
              onChange={(e) => setScrapeUrl(e.target.value)}
            />
          </div>
          <div>
            <label>Table CSS Selector:</label>
            <input
              type="text"
              value={tableSelector}
              onChange={(e) => setTableSelector(e.target.value)}
            />
          </div>
          <button
            className="btn-primary"
            onClick={handleWebScrape}
            disabled={isLoading}
          >
            {isLoading ? <Loader2 size={14} className="animate-spin" /> : <Globe size={14} />}
            Scrape DOM Tables
          </button>
        </div>
      )}

      {ingestMode === 's3' && (
        <div>
          <label>S3 Lakehouse Parquet Key:</label>
          <input
            type="text"
            value={s3Key}
            onChange={(e) => setS3Key(e.target.value)}
          />
          <button
            className="btn-primary"
            style={{ marginTop: '10px', width: '100%' }}
            onClick={() => {
              setDataset({ name: s3Key, headers: ['s3_dataset'], rowCount: 1, sampleRows: [] });
              onSuccess(`Configured S3 Lakehouse path: ${s3Key}`);
            }}
          >
            Attach S3 Dataset
          </button>
        </div>
      )}

      {dataset && (
        <div style={{ marginTop: '16px', padding: '12px', background: 'var(--bg-input)', borderRadius: '6px' }}>
          <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--accent)' }}>
            Active: {dataset.name}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
            {dataset.rowCount} rows • {dataset.headers?.length} columns
          </div>
        </div>
      )}
    </div>
  );
}
