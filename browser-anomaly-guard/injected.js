// injected.js — runs in PAGE context
(function () {
  const originalEval = window.eval;

  window.eval = function () {
    window.postMessage(
      {
        source: "anomaly-guard",
        type: "EVAL_USED"
      },
      "*"
    );
    return originalEval.apply(this, arguments);
  };
})();
