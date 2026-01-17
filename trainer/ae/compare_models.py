import numpy as np
import tensorflow as tf
from trainer.utils.data_loader import load_logged_flows

BASE_MODEL = "models/autoencoder_cicids2018.h5"

def mean_reconstruction_error(model_path, X_eval):
    ae = tf.keras.models.load_model(model_path, compile=False)
    recon = ae.predict(X_eval, verbose=0)
    return float(np.mean(np.mean(np.square(X_eval - recon), axis=1)))


def compare_candidate(candidate_model_path):
    # Load recent benign flows
    X, meta = load_logged_flows()

    # Keep only BENIGN flows
    benign_X = [
        X[i]
        for i, m in enumerate(meta)
        if m.get("final_decision") == "BENIGN"
    ]

    if len(benign_X) < 10:
        return {
            "error": "Not enough benign samples for comparison"
        }

    X_eval = np.asarray(benign_X, dtype=np.float32)

    base_err = mean_reconstruction_error(BASE_MODEL, X_eval)
    cand_err = mean_reconstruction_error(candidate_model_path, X_eval)

    delta = cand_err - base_err

    return {
        "base": {
            "mean_recon_error": base_err
        },
        "candidate": {
            "mean_recon_error": cand_err
        },
        "delta": delta,
        "verdict": "BETTER" if delta < 0 else "WORSE"
    }
