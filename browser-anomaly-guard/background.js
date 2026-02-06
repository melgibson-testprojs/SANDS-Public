let requestCount = 0;
let evalCount = 0;
let riskScore = 0;

chrome.webRequest.onCompleted.addListener(
  () => {
    requestCount++;
  },
  { urls: ["<all_urls>"] }
);

// Receive signals from content script
chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === "eval_detected") {
    evalCount++;
    riskScore += 0.5;
  }
});

// Analyze every 10 seconds
setInterval(() => {
  if (requestCount > 50) {
    riskScore += 1;
  }

  chrome.storage.local.set({
    lastReport: {
      timestamp: Date.now(),
      requestCount,
      evalCount,
      riskScore
    }
  });

  // reset window
  requestCount = 0;
  evalCount = 0;
}, 10000);
