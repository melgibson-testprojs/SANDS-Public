# scripts/resave_sklearn_artifacts.py
from pathlib import Path
import joblib
import shutil

BASE = Path(__file__).resolve().parents[1]
MODELS = BASE / "models"

# Files to resave (backup then overwrite)
to_resave = ["scaler.pkl", "label_encoder.pkl"]

for name in to_resave:
    src = MODELS / name
    if not src.exists():
        print(f"Skipping (not found): {src}")
        continue
    # backup
    backup = MODELS / f"{name}.bak"
    shutil.copy2(src, backup)
    print(f"Backed up {src} -> {backup}")
    # load and resave using current joblib
    obj = joblib.load(src)
    # optionally validate obj has expected attributes
    print(f"Loaded {name}: type={type(obj)}")
    joblib.dump(obj, src)
    print(f"Resaved {src} with current joblib/sklearn.")