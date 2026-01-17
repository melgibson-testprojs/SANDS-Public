import numpy as np
from trainer.utils.data_loader import load_logged_flows


def build_ae_training_set(
    benign_label="BENIGN",
    max_percentile=85,
    min_samples=100,
):
    """
    Builds a safe AE training dataset.
    """

    X, meta = load_logged_flows()

    # Convert meta fields
    final_decisions = np.array([m["final_decision"] for m in meta])
    ae_errors = np.array([m["ae_error"] for m in meta], dtype=float)

    # Step 1: select BENIGN only
    benign_mask = final_decisions == benign_label
    X_benign = X[benign_mask]
    ae_benign_err = ae_errors[benign_mask]

    if len(X_benign) < min_samples:
        raise ValueError(
            f"Not enough benign samples ({len(X_benign)}) "
            f"for incremental training"
        )

    # Step 2: percentile filtering (remove outliers)
    err_threshold = np.percentile(ae_benign_err, max_percentile)
    safe_mask = ae_benign_err <= err_threshold

    X_train = X_benign[safe_mask]

    return {
        "ready": True,
        "stats": {
            "total_logged": len(X),
            "benign_total": len(X_benign),
            "used_for_training": len(X_train),
            "ae_error_percentile": err_threshold,
        }
    }

