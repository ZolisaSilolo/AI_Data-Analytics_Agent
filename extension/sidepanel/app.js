/**
 * OmniAnalyst side panel.
 *
 * Contract: POST {base}/analyze returns 202 {job_id}; the result is fetched
 * from GET {base}/jobs/{job_id} until status is COMPLETED or FAILED.
 */

const POLL_INTERVAL_MS = 1500;
// Longer than the worker's 300s budget so a slow job is not reported as failed.
const POLL_TIMEOUT_MS = 330000;

let activePageData = null;
let pollAbort = null;

document.addEventListener("DOMContentLoaded", () => {
  const apiUrlInput = document.getElementById("apiUrl");
  const btnSaveConfig = document.getElementById("btnSaveConfig");
  const btnScrapePage = document.getElementById("btnScrapePage");
  const btnAnalyze = document.getElementById("btnAnalyze");
  const txtQuery = document.getElementById("txtQuery");
  const statusBox = document.getElementById("statusBox");
  const analysisOutput = document.getElementById("analysisOutput");
  const chartContainer = document.getElementById("chartContainer");

  chrome.storage.local.get(["apiUrl"], (res) => {
    if (res.apiUrl) apiUrlInput.value = res.apiUrl;
  });

  btnSaveConfig.addEventListener("click", () => {
    chrome.storage.local.set({ apiUrl: normalizeBase(apiUrlInput.value) }, () => {
      showStatus("API configuration saved.");
    });
  });

  btnScrapePage.addEventListener("click", async () => {
    showStatus("Extracting tables from the active tab...");
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) {
      showStatus("No active tab found.", true);
      return;
    }

    try {
      // Inject on demand: the extension never installs a persistent script.
      await ensureContentScript(tab.id);
      const res = await chrome.tabs.sendMessage(tab.id, { action: "SCRAPE_PAGE_DATA" });
      if (!res || !res.tables || res.tables.length === 0) {
        showStatus("No HTML tables found on this page.", true);
        return;
      }
      activePageData = res;
      showStatus(`Extracted ${res.tableCount} table(s) from "${res.pageTitle}".`);
    } catch (err) {
      showStatus(`Could not extract data: ${err.message}`, true);
    }
  });

  btnAnalyze.addEventListener("click", async () => {
    const base = normalizeBase(apiUrlInput.value);
    const query = txtQuery.value.trim();

    if (!base) {
      showStatus("Enter your API base URL first (for example https://abc123.execute-api.us-east-1.amazonaws.com/dev).", true);
      return;
    }
    if (!query) {
      showStatus("Enter an analytical question.", true);
      return;
    }
    if (!activePageData) {
      showStatus("Extract a table from the active tab first.", true);
      return;
    }

    cancelPolling();
    const controller = new AbortController();
    pollAbort = controller;

    btnAnalyze.disabled = true;
    chartContainer.innerHTML = "";
    analysisOutput.innerText = "Submitting analysis…";

    try {
      const job = await runAnalysis(
        base,
        { query, page_context: activePageData },
        controller.signal,
        (status) => {
          analysisOutput.innerText = statusText(status);
        }
      );

      const result = job.result || {};
      analysisOutput.innerText = result.analysis || "Analysis completed.";
      renderChart(chartContainer, result.chart_spec);
    } catch (err) {
      if (err.name !== "AbortError") {
        analysisOutput.innerText = `Error: ${err.message}`;
      }
    } finally {
      btnAnalyze.disabled = false;
      pollAbort = null;
    }
  });

  function showStatus(msg, isError = false) {
    statusBox.textContent = msg;
    statusBox.style.borderLeftColor = isError ? "#ef4444" : "#38bdf8";
    statusBox.classList.remove("hidden");
    setTimeout(() => statusBox.classList.add("hidden"), 5000);
  }
});

function statusText(status) {
  switch (status) {
    case "QUEUED":
      return "Queued — waiting for an analysis worker…";
    case "RUNNING":
      return "Running — compiling SQL and executing it deterministically…";
    case "RETRYING":
      return "Retrying — the previous attempt failed transiently…";
    case "COMPLETED":
      return "Completed.";
    case "FAILED":
      return "Failed.";
    default:
      return "Working…";
  }
}

/** Accept a base URL, or a full /analyze or /jobs/<id> URL, and return the base. */
function normalizeBase(raw) {
  let value = String(raw || "").trim().replace(/\/+$/, "");
  if (!value) return "";
  value = value.replace(/\/(analyze|query|health)$/i, "");
  value = value.replace(/\/jobs\/[0-9a-fA-F-]{8,}$/i, "");
  return value.replace(/\/+$/, "");
}

async function ensureContentScript(tabId) {
  try {
    await chrome.tabs.sendMessage(tabId, { action: "PING" });
  } catch {
    await chrome.scripting.executeScript({ target: { tabId }, files: ["content.js"] });
  }
}

async function apiRequest(base, path, { method = "GET", body, signal } = {}) {
  let response;
  try {
    response = await fetch(`${base}${path}`, {
      method,
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal
    });
  } catch (err) {
    if (err.name === "AbortError") throw err;
    throw new Error("Could not reach the analysis API. Check the URL and your connection.");
  }

  let data = {};
  try {
    data = await response.json();
  } catch {
    data = {};
  }

  if (!response.ok) {
    const error = data.error || {};
    const retry = error.retry_after ? ` Retry in ${error.retry_after}s.` : "";
    throw new Error(`${error.message || `Request failed (${response.status}).`}${retry}`);
  }
  return data;
}

async function runAnalysis(base, payload, signal, onStatus) {
  const submitted = await apiRequest(base, "/analyze", { method: "POST", body: payload, signal });
  if (!submitted.job_id) {
    throw new Error("The server did not return a job id.");
  }

  const started = Date.now();
  let delay = POLL_INTERVAL_MS;

  for (;;) {
    const job = await apiRequest(base, `/jobs/${submitted.job_id}`, { method: "GET", signal });
    onStatus(job.status);

    if (job.status === "COMPLETED") {
      if (!job.result) {
        throw new Error("The analysis finished but its result is no longer available.");
      }
      return job;
    }
    if (job.status === "FAILED") {
      const error = job.error || {};
      throw new Error(error.message || "The analysis failed.");
    }
    if (Date.now() - started > POLL_TIMEOUT_MS) {
      throw new Error(
        "The analysis is still running server-side. Re-open this panel in a minute to check the result."
      );
    }

    await new Promise((resolve) => setTimeout(resolve, delay));
    delay = Math.min(Math.round(delay * 1.4), 5000);
  }
}

function cancelPolling() {
  if (pollAbort) pollAbort.abort();
  pollAbort = null;
}

function renderChart(container, chartSpec) {
  if (!chartSpec || !chartSpec.data) return;
  if (typeof Plotly === "undefined") {
    container.innerText = "Chart rendering is unavailable in this extension build.";
    return;
  }
  const layout = {
    ...chartSpec.layout,
    autosize: true,
    margin: { l: 50, r: 20, t: 40, b: 50 },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { color: "#94a3b8", size: 11 }
  };
  Plotly.newPlot(container, chartSpec.data, layout, {
    responsive: true,
    displayModeBar: false
  });
}
