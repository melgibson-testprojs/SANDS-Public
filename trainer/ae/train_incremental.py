import tensorflow as tf
from pathlib import Path
from trainer.ae.build_dataset import build_ae_training_set
from trainer.utils.run_id import next_run_id
from trainer.utils.data_loader import load_logged_flows
import json
import time
import numpy as np

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

BASE_MODEL = "models/autoencoder_cicids2018.h5"
EXPERIMENTS_DIR = Path("models/experiments/ae")
STATE_FILE = EXPERIMENTS_DIR / "training_state.json"

EXPECTED_FEATURES = 77
MIN_SAFE_SAMPLES = 10


# --------------------------------------------------
# TRAINING STATE (DEFENSIVE)
# --------------------------------------------------

def update_state(**kwargs):
    state = {}

    if STATE_FILE.exists():
        try:
            content = STATE_FILE.read_text().strip()
            if content:
                state = json.loads(content)
        except Exception:
            state = {}

    state.update(kwargs)
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


# --------------------------------------------------
# INCREMENTAL TRAINING
# --------------------------------------------------

def train_incremental():
    update_state(status="running", started_at=time.time())

    try:
        # --------------------------------------------------
        # 1. READINESS CHECK (NO DATA PASSED)
        # --------------------------------------------------
        readiness = build_ae_training_set()
        if not readiness.get("ready"):
            update_state(
                status="skipped",
                ended_at=time.time(),
                error=readiness.get("reason"),
            )
            print("❌ Training skipped:", readiness.get("reason"))
            return

        # --------------------------------------------------
        # 2. LOAD RAW FLOWS
        # --------------------------------------------------
        X_raw, meta = load_logged_flows()

        if len(X_raw) == 0:
            raise RuntimeError("No logged flows available")

        # --------------------------------------------------
        # 3. SANITIZE META + FEATURES (CRITICAL FIX)
        # --------------------------------------------------
        clean_X = []
        clean_ae_errors = []

        for i, m in enumerate(meta):
            if not isinstance(m, dict):
                continue

            fd = m.get("final_decision")
            ae = m.get("ae_error")

            if fd != "BENIGN":
                continue

            if ae is None:
                continue

            try:
                ae = float(ae)
            except Exception:
                continue

            x = X_raw[i]

            if x is None:
                continue

            x = np.asarray(x, dtype=np.float32)

            if x.shape[0] != EXPECTED_FEATURES:
                continue

            if not np.isfinite(x).all():
                continue

            clean_X.append(x)
            clean_ae_errors.append(ae)

        if len(clean_X) < MIN_SAFE_SAMPLES:
            raise RuntimeError(
                f"Not enough clean benign samples: {len(clean_X)}"
            )

        X = np.vstack(clean_X)
        ae_errors = np.asarray(clean_ae_errors, dtype=np.float32)

        # --------------------------------------------------
        # 4. SAFE ERROR-BASED FILTERING
        # --------------------------------------------------
        percentile = 95 if len(X) < 500 else 85
        err_threshold = np.percentile(ae_errors, percentile)

        safe_mask = ae_errors <= err_threshold
        X_train = X[safe_mask]

        if X_train.shape[0] < MIN_SAFE_SAMPLES:
            raise RuntimeError(
                f"Too few safe samples after filtering: {X_train.shape[0]}"
            )

        # --------------------------------------------------
        # 5. FINAL SANITY CHECK
        # --------------------------------------------------
        X_train = np.asarray(X_train, dtype=np.float32)
        X_train = np.nan_to_num(
            X_train,
            nan=0.0,
            posinf=0.0,
            neginf=0.0
        )

        if X_train.ndim != 2 or X_train.shape[1] != EXPECTED_FEATURES:
            raise RuntimeError(
                f"Invalid X_train shape: {X_train.shape}"
            )

        if not np.isfinite(X_train).all():
            raise RuntimeError(
                "X_train still contains invalid values"
            )

        # --------------------------------------------------
        # 6. LOAD & TRAIN AUTOENCODER
        # --------------------------------------------------
        ae = tf.keras.models.load_model(
            BASE_MODEL,
            compile=False
        )

        ae.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=1e-4),
            loss="mse",
        )

        history = ae.fit(
            X_train,
            X_train,
            epochs=3,
            batch_size=min(256, len(X_train)),
            shuffle=True,
            verbose=1,
        )



        # --------------------------------------------------
        # 7. SAVE CANDIDATE MODEL
        # --------------------------------------------------
        run_id = next_run_id(EXPERIMENTS_DIR)
        run_dir = EXPERIMENTS_DIR / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        ae.save(run_dir / "autoencoder.h5")

        # -----------------------------
        # SAVE METRICS
        # -----------------------------
        metrics = {
            "model": "autoencoder",
            "base_model": Path(BASE_MODEL).name,
            "samples_used": int(X_train.shape[0]),
            "epochs": int(len(history.history["loss"])),
            "loss_start": float(history.history["loss"][0]),
            "loss_end": float(history.history["loss"][-1]),
            "loss_delta": float(
                history.history["loss"][-1] - history.history["loss"][0]
            ),
            "percentile": percentile,
            "trained_at": time.time(),
        }

        with open(run_dir / "metrics.json", "w") as f:
            json.dump(metrics, f, indent=2)


        # ------------------------ --------------------------
        # 8. UPDATE STATE
        # --------------------------------------------------
        update_state(
            status="completed",
            last_run=run_id,
            ended_at=time.time(),
            error=None,
        )

        print(f"✅ Incremental AE trained successfully: {run_dir}")

    except Exception as e:
        update_state(
            status="failed",
            ended_at=time.time(),
            error=str(e),
        )
        raise
