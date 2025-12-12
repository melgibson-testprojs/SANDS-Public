# scripts/test_batch_predict.py
import pandas as pd
import requests
import os

URL = "http://localhost:8000/batch_predict"
TMP_CSV = "data/test_batch.csv"
os.makedirs("data", exist_ok=True)

# create a small two-row numeric CSV matching 77 columns
row = [
    53,17,125620,2,2,142,180,71,71,71.0,0.0,
    90,90,90.0,0.0,2562.1,31.8,
    41873.3,18120.7,58754.0,25000.0,
    41873.0,41873.0,0.0,41873.0,41873.0,
    41873.0,41873.0,0.0,41873.0,41873.0,
    0,0,0,0,
    40,40,15.9,15.9,
    71,90,80.5,9.5,90.3,
    0,0,0,0,0,0,0,0,
    80.5,71.0,90.0,
    0,0,0,0,0,0,
    2,142,2,180,
    0,0,1,71,
    0,0,0,0,
    0,0,0,0
]
df = pd.DataFrame([row, row])
df.to_csv(TMP_CSV, index=False)

with open(TMP_CSV, "rb") as f:
    resp = requests.post(URL, files={"file": ("test_batch.csv", f, "text/csv")}, timeout=20)
print("status:", resp.status_code)
print(resp.json())
