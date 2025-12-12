# project_settings.py
from pathlib import Path
import os
import pickle
import joblib
import logging
from typing import Optional

ROOT = Path(__file__).resolve().parent
MODELS_DIR = Path(os.getenv("MODEL_DIR", str(ROOT / "models")))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("project_settings")

def list_models():
    """Return list of model files in MODELS_DIR."""
    if not MODELS_DIR.exists():
        logger.warning("MODELS_DIR does not exist: %s", MODELS_DIR)
        return []
    return sorted([p.name for p in MODELS_DIR.iterdir() if p.is_file()])

def load_joblib_safe(name: str):
    """Return loaded object or None. Uses joblib.load."""
    path = MODELS_DIR / name
    if not path.exists():
        logger.debug("joblib: file not found: %s", path)
        return None
    try:
        return joblib.load(path)
    except Exception as e:
        logger.exception("joblib.load failed for %s: %s", path, e)
        return None

def load_pickle_safe(name: str):
    """Return pickle.load object or None."""
    path = MODELS_DIR / name
    if not path.exists():
        logger.debug("pickle: file not found: %s", path)
        return None
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        logger.exception("pickle.load failed for %s: %s", path, e)
        return None

def load_keras_safe(name: str, force_import: bool=False):
    """
    Try to load a Keras model (tf.keras.models.load_model).
    Returns model object or None.
    If tensorflow isn't installed, returns None and logs a warning.
    Set force_import=True to propagate exceptions (for debugging).
    """
    path = MODELS_DIR / name
    if not path.exists():
        logger.debug("keras: file not found: %s", path)
        return None
    try:
        # Deferred import: don't require TensorFlow at module import time
        import importlib
        tf = importlib.import_module("tensorflow")
        model = tf.keras.models.load_model(str(path), compile=False)
        return model
    except ModuleNotFoundError as mnfe:
        logger.warning("tensorflow not available in environment; cannot load keras model %s", path)
        if force_import:
            raise
        return None
    except Exception as e:
        logger.exception("Loading keras model failed for %s: %s", path, e)
        if force_import:
            raise
        return None

def model_path(name: str):
    return MODELS_DIR / name