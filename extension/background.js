/**
 * OmniAnalyst Extension Background Service Worker
 *
 * The side panel talks to the API directly (host_permissions are declared), so
 * this worker only owns browser-level behaviour.
 */

chrome.sidePanel
  .setPanelBehavior({ openPanelOnActionClick: true })
  .catch((error) => console.error(error));
