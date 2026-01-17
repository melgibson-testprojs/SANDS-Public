import numpy as np
import tensorflow as tf
from trainer.utils.data_loader import load_logged_flows
import json
from pathlib import Path

def reconstruction_error(model, X):
    X_hat = model.predict(X, verbose=0)
    return np.mean((X - X_hat) ** 2, axis=1)


def evaluate(base_model_path, candidate_model_path):
    X, meta = load_logged_flows()

    base = tf.keras.models.load_model(base_model_path, compile=False)
    cand = tf.keras.models.load_model(candidate_model_path, compile=False)

    base_err = reconstruction_error(base, X)
    cand_err = reconstruction_error(cand, X)

    metrics = {
        "base": {
            "mean": float(base_err.mean()),
            "p95": float(np.percentile(base_err, 95)),
        },
        "candidate": {
            "mean": float(cand_err.mean()),
            "p95": float(np.percentile(cand_err, 95)),
        },
        "improved": float(np.percentile(cand_err, 95))
                     < float(np.percentile(base_err, 95)),
    }

    out = Path(candidate_model_path).parent / "metrics.json"
    out.write_text(json.dumps(metrics, indent=2))

    return metrics