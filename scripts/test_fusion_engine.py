# scripts/test_fusion_engine.py

import numpy as np
from fusion.fusion_engine import FusionEngine

print("Testing Fusion Engine...\n")

dummy = np.zeros(77)   # adjust if you use 78 features
result = FusionEngine.predict(dummy)

print("Single prediction output:")
for k, v in result.items():
    print(f"  {k}: {v}")

print("\nBatch prediction:")
batch = np.zeros((3, 77))
batch_results = FusionEngine.batch_predict(batch)
for i, r in enumerate(batch_results):
    print(f"Sample {i} -> {r}")
