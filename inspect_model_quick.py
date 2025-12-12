# inspect_model_quick.py
import joblib, numpy as np, sys
p = "models/xgb_model.pkl"   # adjust path if needed
obj = joblib.load(p)
print("TYPE:", type(obj))
print("MODULE:", getattr(obj, "__module__", None))
print("CLASS:", getattr(obj, "__class__", None))
print("HAS predict:", hasattr(obj, "predict"))
if hasattr(obj, "predict"):
    n = getattr(obj, "n_features_in_", None) or 10
    try:
        print("PREDICT ->", obj.predict(np.zeros((1, int(n)))))
    except Exception as e:
        print("predict() raised:", repr(e))