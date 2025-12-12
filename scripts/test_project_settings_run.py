# scripts/test_project_settings_run.py
from project_settings import MODELS_DIR, list_models, load_joblib_safe, load_keras_safe, model_path
print("MODELS_DIR:", MODELS_DIR)
print("Found:", list_models())

# Test joblib loads
for name in list_models():
    if name.endswith(".pkl"):
        o = load_joblib_safe(name)
        print(f"-> {name}: {'LOADED' if o is not None else 'FAILED'}; type={type(o) if o is not None else None}")

# Test keras load (deferred)
h5 = "autoencoder_cicids2018.h5"
ae = load_keras_safe(h5)
print("Autoencoder load:", "OK" if ae is not None else "NOT LOADED")