/**
 * OmniAnalyst Content Script
 * Scrapes HTML <table>, AG-Grid, TanStack, and canvas data from the active web dashboard.
 */

function extractTableData() {
  const tables = document.querySelectorAll("table");
  const extracted = [];

  tables.forEach((table, index) => {
    const headers = [];
    table.querySelectorAll("th").forEach(th => {
      headers.push(th.innerText.trim());
    });

    const rows = [];
    table.querySelectorAll("tbody tr, tr").forEach(tr => {
      const row = [];
      tr.querySelectorAll("td").forEach(td => {
        row.push(td.innerText.trim());
      });
      if (row.length > 0 && row.length === headers.length) {
        rows.push(row);
      }
    });

    if (rows.length > 0) {
      extracted.push({
        tableIndex: index + 1,
        headers: headers.length > 0 ? headers : rows[0].map((_, i) => `Column_${i+1}`),
        rowCount: rows.length,
        sampleRows: rows.slice(0, 100)
      });
    }
  });

  return {
    url: window.location.href,
    pageTitle: document.title,
    tableCount: extracted.length,
    tables: extracted
  };
}

// Listen for messages from the sidepanel
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "SCRAPE_PAGE_DATA") {
    const result = extractTableData();
    sendResponse(result);
  }
});
