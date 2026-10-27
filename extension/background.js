/**
 * OmniAnalyst Extension Background Service Worker
 * Routes messages between browser tabs, content scripts, and AWS Serverless API Gateway.
 */

// Enable sidepanel on action icon click
chrome.sidePanel
  .setPanelBehavior({ openPanelOnActionClick: true })
  .catch((error) => console.error(error));

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "EXECUTE_API_REQUEST") {
    const { endpoint, payload, apiKey } = request;
    
    fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(apiKey ? { "x-api-key": apiKey } : {})
      },
      body: JSON.stringify(payload)
    })
      .then(async (res) => {
        const data = await res.json();
        sendResponse({ success: res.ok, data });
      })
      .catch((err) => {
        sendResponse({ success: false, error: err.message });
      });

    return true; // Keep channel open for async response
  }
});
