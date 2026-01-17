import shutil
from pathlib import Path
from datetime import datetime

BASE_MODEL = Path("models/autoencoder_cicids2018.h5")
BACKUP_DIR = Path("models/backups")


def promote(candidate_path):
    BACKUP_DIR.mkdir(exist_ok=True)

    # Backup current model
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"autoencoder_{ts}.h5"
    shutil.copy(BASE_MODEL, backup_path)

    # Promote candidate
    shutil.copy(candidate_path, BASE_MODEL)

    print("✅ Model promoted")
    print("🔙 Backup saved at:", backup_path)
