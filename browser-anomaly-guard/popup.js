chrome.storage.local.get("lastReport", (data) => {
  const riskEl = document.getElementById("risk");
  const reqEl = document.getElementById("req");
  const evalEl = document.getElementById("eval");

  if (!data.lastReport) {
    riskEl.textContent = "Risk: LOW";
    riskEl.className = "risk low";
    return;
  }

  const { riskScore, requestCount, evalCount } = data.lastReport;

  let level = "LOW";
  let cls = "low";

  if (riskScore >= 3) {
    level = "HIGH ⚠️";
    cls = "high";
  } else if (riskScore >= 1.5) {
    level = "MEDIUM ⚠️";
    cls = "medium";
  }

  riskEl.textContent = `Risk: ${level}`;
  riskEl.className = `risk ${cls}`;

  reqEl.textContent = `Requests (10s): ${requestCount}`;
  evalEl.textContent = `eval() calls: ${evalCount}`;
});

// View full report
document.getElementById("view").onclick = () => {
  chrome.storage.local.get("lastReport", (data) => {
    alert(JSON.stringify(data.lastReport || {}, null, 2));
  });
};

// Reset data
document.getElementById("reset").onclick = () => {
  chrome.storage.local.clear(() => {
    location.reload();
  });
};
