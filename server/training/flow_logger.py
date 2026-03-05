import time
import json
from pathlib import Path
import numpy as np

LOG_DIR = Path("models/logs")
LOG_FILE = LOG_DIR / "ae_training.jsonl"

LOG_DIR.mkdir(parents=True, exist_ok=True)


def log_flow_for_training(
    *,
    features: np.ndarray,
    result: dict,
    agent_id: str,
    logical_agent_id: str,
):
    """
    Append ONE flow record for offline incremental AE training.
    Must NEVER break inference.
    """

    try:
        row = {
            "ts": time.time(),
            "agent_id": agent_id,
            "logical_agent_id": logical_agent_id,

            # 21 scaled features
            "features": features.astype(float).tolist(),

            # prediction context
            "final_decision": result.get("final_decision"),
            "ae_error": float(result.get("reconstruction_error", 0.0)),
            "xgb_pred": result.get("supervised_pred"),  # STRING (BENIGN/ATTACK)
        }

        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")

    except Exception as e:
        print("FLOW LOGGER ERROR:", e)
