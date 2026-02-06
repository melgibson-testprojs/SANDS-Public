// Inject external script into page context (CSP-safe)
const injectedScript = document.createElement("script");
injectedScript.src = chrome.runtime.getURL("injected.js");
injectedScript.type = "text/javascript";
(document.head || document.documentElement).appendChild(injectedScript);

// Listen for messages from injected page script
window.addEventListener("message", (event) => {
  if (
    event.data &&
    event.data.source === "anomaly-guard" &&
    event.data.type === "EVAL_USED"
  ) {
    chrome.runtime.sendMessage({ type: "eval_detected" });
  }
});
