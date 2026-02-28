# server/fusion_layer.py        ----- REPLACED WITH FUSIONN ENGINE
"""
Robust fusion layer for SANDS

- Uses XGBoost (if present) and Autoencoder (if present).
- If either model is missing, falls back gracefully.
- Returns a list of dicts, one per input row:
  {
    "final_decision": "ATTACK"|"BENIGN"|"SUSPICIOUS",
    "supervised_pred": "BENIGN"|"ATTACK"|None,
    "xgb_flag": bool,
    "ae_flag": bool,
    "reconstruction_error": float|None
  }
"""

from typing import List, Optional, Dict
import os
import numpy as np
import logging

from project_settings import load_joblib_safe, load_keras_safe, logger

# Configuration: threshold for AE reconstruction error (tune via env)
RECON_THRESHOLD = float(os.getenv("AE_RECON_THRESHOLD", "0.015"))

# Load supervised model (XGBoost sklearn wrapper) and AE via safe loaders
xgb_model = load_joblib_safe("xgb_model.pkl")
if xgb_model is not None:
    logger.info("fusion_layer: loaded supervised model (xgb_model.pkl) -> %s", type(xgb_model))
else:
    logger.info("fusion_layer: supervised model not available; will use AE-only or rule-based logic.")

autoencoder = load_keras_safe("autoencoder_cicids2018.h5")
if autoencoder is not None:
    logger.info("fusion_layer: loaded autoencoder (autoencoder_cicids2018.h5)")
else:
    logger.info("fusion_layer: autoencoder not available.")

def _ae_flags_and_errors(X_scaled: np.ndarray) -> (Optional[np.ndarray], List[bool]):
    """
    If AE is available, compute reconstruction error and boolean anomaly flags.
    Returns (reconstruction_error_array_or_None, ae_flags_list).
    """
    if autoencoder is None:
        return None, [False] * X_scaled.shape[0]

    try:
        X_rec = autoencoder.predict(X_scaled)
        # mean squared error per sample
        rec_err = np.mean(np.square(X_scaled - X_rec), axis=1)
        ae_flags = (rec_err > RECON_THRESHOLD).tolist()
        return rec_err, ae_flags
    except Exception as e:
        logger.exception("fusion_layer: autoencoder predict failed: %s", e)
        return None, [False] * X_scaled.shape[0]

def _xgb_flags_and_preds(X_scaled: np.ndarray) -> (List[bool], List[Optional[str]]):
    """
    If XGB model is available, run predict and return boolean flags and supervised labels.
    supervised labels are 'BENIGN' or 'ATTACK'; if model missing, returns lists of defaults.
    """
    n = X_scaled.shape[0]
    if xgb_model is None:
        return [False] * n, [None] * n

    try:
        raw_preds = xgb_model.predict(X_scaled)  # may be array of 0/1 or labels
        # convert to ints/bools if numeric; otherwise try mapping
        xgb_flags = []
        supervised_labels = []
        for p in raw_preds:
            try:
                p_int = int(p)
                flag = (p_int != 0)
                lbl = "BENIGN" if p_int == 0 else "ATTACK"
            except Exception:
                # if predict returned string labels
                flag = str(p).upper() != "BENIGN"
                lbl = str(p).upper()
            xgb_flags.append(bool(flag))
            supervised_labels.append(lbl)
        return xgb_flags, supervised_labels
    except Exception as e:
        logger.exception("fusion_layer: xgb_model.predict failed: %s", e)
        return [False] * n, [None] * n

def predict_fusion(X_scaled: np.ndarray) -> List[Dict]:
    """
    Main entrypoint.

    X_scaled: numpy array shape (n_samples, n_features).
      - Important: must be scaled already if your pipeline expects scaled input.
      - If your agent sends scaled vectors, pass them directly.
      - If server receives raw features, call scaler.transform before calling this.

    Returns list of dicts (one per sample).
    """
    if X_scaled is None:
        raise ValueError("X_scaled is required and cannot be None")

    if not isinstance(X_scaled, np.ndarray):
        X_scaled = np.array(X_scaled, dtype=float)

    n = X_scaled.shape[0]

    # AE
    rec_err, ae_flags = _ae_flags_and_errors(X_scaled)

    # XGB
    xgb_flags, supervised_preds = _xgb_flags_and_preds(X_scaled)

    results = []
    for i in range(n):
        xgb_flag = bool(xgb_flags[i]) if i < len(xgb_flags) else False
        ae_flag = bool(ae_flags[i]) if i < len(ae_flags) else False
        rec = float(rec_err[i]) if (rec_err is not None and i < len(rec_err)) else None
        sup = supervised_preds[i] if i < len(supervised_preds) else None

        # Decision logic:
        # - If either model signals attack -> ATTACK
        # - If supervised absent and AE says anomaly -> SUSPICIOUS
        # - Else BENIGN
        if xgb_flag or ae_flag:
            final_decision = "ATTACK"
        else:
            final_decision = "BENIGN"

        if sup is None and ae_flag and not xgb_flag:
            # if supervised not available but AE raised, mark as SUSPICIOUS (optional)
            final_decision = "SUSPICIOUS"

        result = {
            "final_decision": final_decision,
            "supervised_pred": sup,               # "BENIGN"/"ATTACK" or None
            "xgb_flag": xgb_flag,
            "ae_flag": ae_flag,
            "reconstruction_error": rec
        }
        results.append(result)

    return results