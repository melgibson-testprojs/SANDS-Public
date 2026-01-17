import json
import numpy as np
from pathlib import Path


LOG_FILE = Path("models/logs/ae_training.jsonl")
EXPECTED_FEATURES = 77


def load_logged_flows():
    """
    Loads logged flows for AE incremental training.
    Returns:
        X : np.ndarray (N, 77)
        meta : list of dicts (optional context)
    """
    if not LOG_FILE.exists():
        raise FileNotFoundError(f"{LOG_FILE} not found")

    X = []
    meta = []

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            row = json.loads(line)

            features = row.get("features")

            if features is None:
                continue

            if len(features) != EXPECTED_FEATURES:
                raise ValueError(
                    f"Feature length mismatch at line {line_no}: "
                    f"{len(features)} != {EXPECTED_FEATURES}"
                )

            X.append(features)
            meta.append({
                "final_decision": row.get("final_decision"),
                "ae_error": row.get("ae_error"),
                "xgb_pred": row.get("xgb_pred"),
            })

    return np.array(X, dtype=float), meta
