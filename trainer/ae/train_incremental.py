import tensorflow as tf
from pathlib import Path
from trainer.ae.build_dataset import build_ae_training_set
from trainer.utils.run_id import next_run_id

BASE_MODEL = "models/autoencoder_cicids2018.h5"
EXPERIMENTS_DIR = Path("models/experiments/ae")


def train_incremental():
    data = build_ae_training_set()

    if not data["ready"]:
        print("❌ Training skipped:", data["reason"])
        print(data["stats"])
        return

    X_train = data["X_train"]

    # Load base AE safely
    ae = tf.keras.models.load_model(
        BASE_MODEL,
        compile=False
    )

    # Recompile explicitly
    ae.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-4),
        loss="mse"
    )

    # Train (small, conservative)
    ae.fit(
        X_train,
        epochs=3,
        batch_size=256,
        shuffle=True,
        verbose=1,
    )

    # Save candidate
    run_id = next_run_id(EXPERIMENTS_DIR)
    run_dir = EXPERIMENTS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    ae.save(run_dir / "autoencoder.h5")

    print(f"✅ Incremental AE trained: {run_dir}")
