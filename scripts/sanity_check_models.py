# sanity_check_models.py
"""
Simple sanity checks for model files in Phase2.1/models/.
Run: python scripts/sanity_check_models.py
"""

import sys
import numpy as np
from pathlib import Path
import traceback
import importlib

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))  # so project_settings imports work
from project_settings import MODELS_DIR, list_models, load_joblib_safe, load_pickle_safe, load_keras_safe, model_path

print("MODELS_DIR:", MODELS_DIR)
files = list_models()
if not files:
    print("No model files found in models/ -- place scaler.pkl, autoencoder_cicids2018.h5, xgb_model.pkl etc. in the models folder.")
    sys.exit(0)

print("Found files:", files)
print("-" * 60)

# Inspect joblib/pickle-loaded models
for name in files:
    p = model_path(name)
    print(f"\nInspecting {name} ({p.suffix})")
    # quick size
    try:
        print("  size (KB):", round(p.stat().st_size/1024, 2))
    except Exception:
        pass

    # If it's a common Keras extension, try loading via load_keras_safe (deferred)
    if name.endswith((".h5", ".keras")):
        print("  → Attempting keras load (deferred). If tensorflow is not installed this will skip.")
        m = load_keras_safe(name)
        if m is None:
            print("    keras model NOT loaded (tensorflow missing or load failed).")
        else:
            print("    keras model loaded OK. Summary:")
            try:
                m.summary()
            except Exception:
                print("    (Could not print summary)")
        continue

    # Try joblib / pickle
    obj = None
    for loader_name, loader in (("joblib", load_joblib_safe), ("pickle", load_pickle_safe)):
        try:
            obj = loader(name)
            if obj is not None:
                print(f"  → Loaded with {loader_name}")
                break
        except Exception as e:
            print(f"  Loader {loader_name} raised: {e}")
            traceback.print_exc(limit=2)

    if obj is None:
        print("  → Could not load model via joblib/pickle (or it's a TF saved-model dir).")
        continue

    # Inspect object
    try:
        print("  TYPE:", type(obj))
        print("  MODULE:", getattr(obj, "__module__", None))
        print("  CLASS:", getattr(obj, "__class__", None))
        print("  HAS predict:", hasattr(obj, "predict"))
        # if sklearn pipeline, show steps
        if hasattr(obj, "steps"):
            try:
                print("  Pipeline steps:", obj.steps)
            except Exception:
                pass

        # Try a safe predict if predict exists
        if hasattr(obj, "predict"):
            print("  → Attempting a tiny predict(...) with zeros (wrapped).")
            try:
                # pick number of input features heuristically
                n_in = getattr(obj, "n_features_in_", None)
                if n_in is None:
                    # some sklearn models have coef_.shape etc. fallback to 10
                    n_in = 10
                X = np.zeros((1, int(n_in)))
                y = obj.predict(X)
                print("    predict OK, output:", y)
            except Exception as e:
                print("    predict raised:", repr(e))
        else:
            print("  → Object has no predict() method.")
    except Exception as e:
        print("  Inspect failed:", e)
        traceback.print_exc(limit=2)

print("\nSanity check complete.")
