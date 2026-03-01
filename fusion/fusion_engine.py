# fusion/fusion_engine.py
import os
import json
import numpy as np
from functools import lru_cache
from typing import Dict, List, Union

from project_settings import (
    load_joblib_safe,
    load_keras_safe
)

# ============================================================
# CONFIG
# ============================================================

AE_THRESHOLD = 1.75 #fake for synthetic 32 else 1.75
BASE_AE_PATH = os.path.join("models", "autoencoder_cicids2018.h5")
AE_EXPERIMENTS_DIR = os.path.join("models", "experiments", "ae")

# ============================================================
# MODEL LOADING (cached)
# ============================================================

@lru_cache()
def get_xgb_model():
    return load_joblib_safe("xgb_model.pkl")


@lru_cache(maxsize=16)
def get_autoencoder(version: str):
    if version == "base":
        model = load_keras_safe("autoencoder_cicids2018.h5")
        threshold = 1.75 #fake for synthetic 32 else 1.75
        return model, threshold

    # incremental runs
    metrics_path = os.path.join(AE_EXPERIMENTS_DIR, version, "metrics.json")

    relative_path = os.path.join(
        "experiments",
        "ae",
        version,
        "autoencoder.h5"
    )

    model = load_keras_safe(relative_path)

    if model is None:
        raise RuntimeError(f"Failed to load autoencoder: {relative_path}")

    threshold = 1.75 #fake for synthetic 32 else 1.75
    if os.path.exists(metrics_path):
        with open(metrics_path, "r") as f:
            metrics = json.load(f)
            threshold = metrics.get("threshold", threshold)

    return model, threshold

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _ensure_2d(x: Union[List[float], np.ndarray]) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        return x.reshape(1, -1)
    return x


def _supervised_label(xgb_output: int) -> str:
    return "ATTACK" if xgb_output == 1 else "BENIGN"


def _ae_flag(mse: float) -> str:
    return "ANOMALY" if mse > AE_THRESHOLD else "NORMAL"


def _fusion_decision(label: str, ae_flag: str) -> str:
    if label == "BENIGN" and ae_flag == "NORMAL":
        return "BENIGN"
    if label == "BENIGN" and ae_flag == "ANOMALY":
        return "SUSPICIOUS"
    return "ATTACK"

# ============================================================
# MAIN FUSION ENGINE
# ============================================================

class FusionEngine:
    """
    Central inference engine for:
        - XGBoost supervised predictions
        - Autoencoder reconstruction error
        - Unified fusion decision

    IMPORTANT:
        Input features MUST already be scaled.
    """

    @staticmethod
    def predict(features: Union[List[float], np.ndarray], model_version: str = "base") -> Dict:
        X = _ensure_2d(features)

        xgb = get_xgb_model()
        ae, threshold = get_autoencoder(model_version)

        # Supervised prediction
        xgb_raw = xgb.predict(X)[0]
        label = _supervised_label(int(xgb_raw))

        # Autoencoder reconstruction error
        X_reconstructed = ae.predict(X, verbose=0)
        mse = float(np.mean((X - X_reconstructed) ** 2))
        ae_flag = "ANOMALY" if mse > threshold else "NORMAL"

        final_decision = _fusion_decision(label, ae_flag)

        return {
            "supervised_pred": label,
            "autoencoder_flag": ae_flag,
            "reconstruction_error": mse,
            "final_decision": final_decision,
            "model_version": model_version
        }

    @staticmethod
    def batch_predict(batch_features: Union[List[List[float]], np.ndarray], model_version: str = "base") -> List[Dict]:
        X = _ensure_2d(batch_features)

        xgb = get_xgb_model()
        ae, threshold = get_autoencoder(model_version)

        xgb_raw = xgb.predict(X)
        X_reconstructed = ae.predict(X)
        mse_arr = np.mean((X - X_reconstructed) ** 2, axis=1)

        results = []

        for i in range(len(X)):
            label = _supervised_label(int(xgb_raw[i]))
            ae_flag = "ANOMALY" if mse_arr[i] > threshold else "NORMAL"
            final = _fusion_decision(label, ae_flag)

            results.append({
                "supervised_pred": label,
                "autoencoder_flag": ae_flag,
                "reconstruction_error": float(mse_arr[i]),
                "final_decision": final
            })

        return results
