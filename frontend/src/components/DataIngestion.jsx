import React, { useRef, useState } from 'react';
import { Upload, Database, FileText, Loader2, CheckCircle2 } from 'lucide-react';
import { uploadDataset, ApiError } from '../lib/api.js';

const DATASET_KEY_RE = /^uploads\/[A-Za-z0-9_-]{1,64}\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.(csv|parquet)$/;

export default function DataIngestion({ dataset, setDataset, apiEndpoint, onError, onSuccess }) {
  const [ingestMode, setIngestMode] = useState('upload'); // 'upload' | 's3'
  const [s3Key, setS3Key] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const abortRef = useRef(null);

  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;

    if (!/\.(csv|parquet)$/i.test(file.name)) {
      onError('Only .csv and .parquet files are supported.');
      return;
    }
    if (file.size === 0) {
      onError('The selected file is empty.');
      return;
    }

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setIsUploading(true);
    try {
      const { dataset_key } = await uploadDataset(apiEndpoint, file, { signal: controller.signal });
      setDataset({
        key: dataset_key,
        name: file.name,
        sizeBytes: file.size,
        rowCount: null,
        headers: null
      });
      onSuccess(`${file.name} uploaded. Run an analysis to profile it.`);
    } catch (err) {
      if (err.name !== 'AbortError') {
        onError(err instanceof ApiError ? err.message : 'Upload failed.');
      }
    } finally {
      setIsUploading(false);
    }
  };

  const attachExistingKey = () => {
    const key = s3Key.trim();
    if (!DATASET_KEY_RE.test(key)) {
      onError('Enter a dataset key in the form uploads/<workspace>/<uuid>.csv.');
      return;
    }
    setDataset({ key, name: key.split('/').pop(), rowCount: null, headers: null });
    onSuccess('Dataset attached from the lakehouse.');
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
          className={`btn-secondary ${ingestMode === 's3' ? 'active' : ''}`}
          style={{ flex: 1, padding: '6px 8px', fontSize: '11px' }}
          onClick={() => setIngestMode('s3')}
        >
          <FileText size={13} /> Lakehouse Key
        </button>
      </div>

      {ingestMode === 'upload' && (
        <div>
          <label>Choose a CSV or Parquet file:</label>
          <input
            type="file"
            accept=".csv,.parquet"
            onChange={handleFileUpload}
            disabled={isUploading}
          />
          <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '8px' }}>
            Files upload directly to encrypted S3 (max 50 MB). Use the browser extension to
            capture live dashboard tables.
          </p>
          {isUploading && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '10px', fontSize: '12px' }}>
              <Loader2 size={14} className="animate-spin" /> Uploading to the lakehouse...
            </div>
          )}
        </div>
      )}

      {ingestMode === 's3' && (
        <div>
          <label>Existing lakehouse dataset key:</label>
          <input
            type="text"
            placeholder="uploads/<workspace>/<uuid>.csv"
            value={s3Key}
            onChange={(e) => setS3Key(e.target.value)}
          />
          <button
            className="btn-primary"
            style={{ marginTop: '10px', width: '100%' }}
            onClick={attachExistingKey}
          >
            Attach Dataset
          </button>
        </div>
      )}

      {dataset && (
        <div style={{ marginTop: '16px', padding: '12px', background: 'var(--bg-input)', borderRadius: '6px' }}>
          <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--accent)', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <CheckCircle2 size={13} /> {dataset.name}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
            {dataset.rowCount != null
              ? `${dataset.rowCount.toLocaleString()} rows • ${dataset.headers?.length || 0} columns`
              : 'Uploaded • profile available after analysis'}
          </div>
        </div>
      )}
    </div>
  );
}
