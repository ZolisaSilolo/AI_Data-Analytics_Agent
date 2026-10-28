/**
 * API client for the OmniAnalyst async job contract.
 *
 * Every call either resolves with the parsed JSON body or throws ApiError with
 * a stable `code` from the backend error envelope.
 */

export class ApiError extends Error {
  constructor(code, message, status = 0, retryAfter = null) {
    super(message || 'Request failed');
    this.name = 'ApiError';
    this.code = code || `HTTP_${status}`;
    this.status = status;
    this.retryAfter = retryAfter;
  }
}

const base = (endpoint) => String(endpoint || '').replace(/\/+$/, '');

async function parseJson(response) {
  try {
    return await response.json();
  } catch {
    return {};
  }
}

export async function request(apiEndpoint, path, { method = 'POST', body, signal } = {}) {
  if (!apiEndpoint) {
    throw new ApiError('NO_ENDPOINT', 'No API endpoint configured. Set VITE_API_ENDPOINT or use settings.');
  }

  let response;
  try {
    response = await fetch(`${base(apiEndpoint)}${path}`, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal
    });
  } catch (err) {
    if (err.name === 'AbortError') throw err;
    throw new ApiError('NETWORK_ERROR', 'Could not reach the analysis API. Check your connection.');
  }

  const data = await parseJson(response);
  if (!response.ok) {
    const error = data.error || {};
    throw new ApiError(
      error.code || `HTTP_${response.status}`,
      error.message || `Request failed with status ${response.status}.`,
      response.status,
      error.retry_after ?? null
    );
  }
  return data;
}

/**
 * Upload a dataset directly to S3 using a server-issued presigned POST.
 * The object key is chosen by the server, never by the browser.
 */
export async function uploadDataset(apiEndpoint, file, { signal, onProgress } = {}) {
  const presigned = await request(apiEndpoint, '/upload/presign', {
    method: 'POST',
    body: {
      filename: file.name,
      size: file.size,
      content_type: file.type || (file.name.endsWith('.parquet') ? 'application/vnd.apache.parquet' : 'text/csv')
    },
    signal
  });

  if (file.size > (presigned.max_bytes || Infinity)) {
    throw new ApiError('FILE_TOO_LARGE', `Uploads are limited to ${Math.floor((presigned.max_bytes || 0) / (1024 * 1024))} MB.`);
  }

  const form = new FormData();
  Object.entries(presigned.upload_fields || {}).forEach(([key, value]) => form.append(key, value));
  form.append('file', file);

  onProgress?.('uploading');
  let upload;
  try {
    upload = await fetch(presigned.upload_url, { method: 'POST', body: form, signal });
  } catch (err) {
    if (err.name === 'AbortError') throw err;
    throw new ApiError('UPLOAD_FAILED', 'The dataset upload failed. Please retry.');
  }
  if (!upload.ok) {
    const detail = await upload.text().catch(() => '');
    if (upload.status === 403) {
      throw new ApiError('UPLOAD_REJECTED', 'The upload link expired or the file exceeded the size limit.');
    }
    throw new ApiError('UPLOAD_FAILED', `The dataset upload was rejected (${upload.status}). ${detail.slice(0, 120)}`);
  }
  onProgress?.('uploaded');

  return { dataset_key: presigned.dataset_key };
}

/**
 * Poll a job until it reaches a terminal state or the timeout elapses.
 *
 * The timeout must exceed the worker's 300s budget, otherwise a slow analysis is
 * reported as failed while it is still running.
 */
export async function pollJob(
  apiEndpoint,
  jobId,
  { intervalMs = 1500, timeoutMs = 330000, signal, onTick } = {}
) {
  const started = Date.now();
  let delay = intervalMs;

  for (;;) {
    if (signal?.aborted) throw new DOMException('Aborted', 'AbortError');

    const job = await request(apiEndpoint, `/jobs/${jobId}`, { method: 'GET', signal });
    onTick?.(job);

    if (job.status === 'COMPLETED') {
      if (!job.result) {
        throw new ApiError('RESULT_UNAVAILABLE', 'The analysis finished but its result is no longer available.');
      }
      return job;
    }
    if (job.status === 'FAILED') {
      const error = job.error || {};
      throw new ApiError(error.code || 'JOB_FAILED', error.message || 'The analysis failed.', 0, error.retry_after ?? null);
    }
    if (Date.now() - started > timeoutMs) {
      throw new ApiError('JOB_TIMEOUT', 'The analysis is taking longer than expected. It will keep running; try again shortly.');
    }

    await new Promise((resolve) => setTimeout(resolve, delay));
    delay = Math.min(Math.round(delay * 1.4), 5000);
  }
}

export async function analyze(apiEndpoint, payload, options = {}) {
  return request(apiEndpoint, '/analyze', { method: 'POST', body: payload, ...options });
}
