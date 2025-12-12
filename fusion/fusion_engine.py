# fusion/fusion_engine.py

import numpy as np
from functools import lru_cache
from typing import Dict, List, Union

from project_settings import (
    model_path,
    load_joblib_safe,
    load_keras_safe
)

# ============================================================
# CONFIG (matches your working server configuration)
# ============================================================

AE_THRESHOLD = 96.36818779649906   # anomaly threshold used in your past server

# ============================================================
# MODEL LOADING (cached)
# ============================================================

@lru_cache()
def get_xgb_model():
    return load_joblib_safe("xgb_model.pkl")


@lru_cache()
def get_scaler():
    return load_joblib_safe("scaler.pkl")


@lru_cache()
def get_autoencoder():
    return load_keras_safe("autoencoder_cicids2018.h5")


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _ensure_2d(x: Union[List[float], np.ndarray]) -> np.ndarray:
    """
    Ensures input is shaped as (1, n_features) or (batch, n_features)
    """
    x = np.asarray(x, dtype=float)

    if x.ndim == 1:
        return x.reshape(1, -1)
    return x


def _supervised_label(xgb_output: int) -> str:
    """
    Convert numeric XGB output to BENIGN/ATTACK
    """
    return "ATTACK" if xgb_output == 1 else "BENIGN"


def _ae_flag(mse: float) -> str:
    """
    Convert reconstruction error to NORMAL/ANOMALY
    """
    return "ANOMALY" if mse > AE_THRESHOLD else "NORMAL"


def _fusion_decision(label: str, ae_flag: str) -> str:
    """
    Same fusion logic as your FastAPI server:

    XGB -> BENIGN | ATTACK
    AE  -> NORMAL | ANOMALY

    FUSION:
        BENIGN + NORMAL      -> BENIGN
        BENIGN + ANOMALY     -> SUSPICIOUS
        ATTACK + ANYTHING    -> ATTACK
    """
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
    """

    @staticmethod
    def predict(features: Union[List[float], np.ndarray]) -> Dict:
        """
        Predict for a single feature vector
        Returns dict with supervised_pred, autoencoder_flag, reconstruction_error, final_decision
        """
        X = _ensure_2d(features)

        scaler = get_scaler()
        xgb = get_xgb_model()
        ae = get_autoencoder()

        # Scale
        X_scaled = scaler.transform(X)

        # Supervised model prediction
        xgb_raw = xgb.predict(X_scaled)[0]
        label = _supervised_label(int(xgb_raw))

        # Autoencoder reconstruction error
        X_reconstructed = ae.predict(X_scaled)
        mse = float(np.mean((X_scaled - X_reconstructed) ** 2))

        ae_flag = _ae_flag(mse)

        # Final fusion decision
        final_decision = _fusion_decision(label, ae_flag)

        return {
            "supervised_pred": label,
            "autoencoder_flag": ae_flag,
            "reconstruction_error": mse,
            "final_decision": final_decision
        }

    @staticmethod
    def batch_predict(batch_features: Union[List[List[float]], np.ndarray]) -> List[Dict]:
        """
        Batch prediction for multiple flows in one call.
        Returns list of result dicts.
        """
        X = _ensure_2d(batch_features)

        scaler = get_scaler()
        xgb = get_xgb_model()
        ae = get_autoencoder()

        X_scaled = scaler.transform(X)

        # Supervised predictions
        xgb_raw = xgb.predict(X_scaled)

        # Autoencoder reconstruction
        X_reconstructed = ae.predict(X_scaled)
        mse_arr = np.mean((X_scaled - X_reconstructed) ** 2, axis=1)

        results = []

        for i in range(len(X)):
            label = _supervised_label(int(xgb_raw[i]))
            ae_flag = _ae_flag(float(mse_arr[i]))
            final = _fusion_decision(label, ae_flag)

            results.append({
                "supervised_pred": label,
                "autoencoder_flag": ae_flag,
                "reconstruction_error": float(mse_arr[i]),
                "final_decision": final
            })

        return results
