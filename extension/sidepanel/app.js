let activePageData = null;

document.addEventListener("DOMContentLoaded", () => {
  const apiUrlInput = document.getElementById("apiUrl");
  const btnSaveConfig = document.getElementById("btnSaveConfig");
  const btnScrapePage = document.getElementById("btnScrapePage");
  const btnAnalyze = document.getElementById("btnAnalyze");
  const txtQuery = document.getElementById("txtQuery");
  const statusBox = document.getElementById("statusBox");
  const analysisOutput = document.getElementById("analysisOutput");

  // Load saved API URL
  chrome.storage.local.get(["apiUrl"], (res) => {
    if (res.apiUrl) apiUrlInput.value = res.apiUrl;
  });

  btnSaveConfig.addEventListener("click", () => {
    chrome.storage.local.set({ apiUrl: apiUrlInput.value.trim() }, () => {
      showStatus("API configuration saved!");
    });
  });

  btnScrapePage.addEventListener("click", async () => {
    showStatus("Extracting DOM tables from active tab...");
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) {
      showStatus("No active tab found.", true);
      return;
    }

    chrome.tabs.sendMessage(tab.id, { action: "SCRAPE_PAGE_DATA" }, (res) => {
      if (chrome.runtime.lastError || !res) {
        showStatus("Could not extract data. Ensure page contains HTML tables.", true);
        return;
      }
      activePageData = res;
      showStatus(`Extracted ${res.tableCount} tables from: ${res.pageTitle}`);
    });
  });

  btnAnalyze.addEventListener("click", () => {
    const query = txtQuery.value.trim();
    const endpoint = apiUrlInput.value.trim();

    if (!endpoint) {
      showStatus("Please specify your AWS API Gateway endpoint first.", true);
      return;
    }
    if (!query) {
      showStatus("Please enter an analytical question.", true);
      return;
    }

    analysisOutput.innerText = "Connecting to Amazon Bedrock & executing deterministic calculations...";

    const payload = {
      query: query,
      page_context: activePageData
    };

    chrome.runtime.sendMessage(
      { action: "EXECUTE_API_REQUEST", endpoint, payload },
      (res) => {
        if (!res.success) {
          analysisOutput.innerText = `Error: ${res.error || JSON.stringify(res.data)}`;
          return;
        }

        const data = res.data;
        analysisOutput.innerText = data.analysis || "Analysis completed.";

        if (data.chart_spec) {
          Plotly.newPlot("chartContainer", data.chart_spec.data, data.chart_spec.layout);
        }
      }
    );
  });

  function showStatus(msg, isError = false) {
    statusBox.textContent = msg;
    statusBox.style.borderLeftColor = isError ? "#ef4444" : "#38bdf8";
    statusBox.classList.remove("hidden");
    setTimeout(() => statusBox.classList.add("hidden"), 4000);
  }
});
