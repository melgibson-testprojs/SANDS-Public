# server/main.py

from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List

import numpy as np
import pandas as pd
import os
import shutil

from fusion.fusion_engine import FusionEngine


app = FastAPI(
    title="SwarmSec Phase 2.1 IDS Server",
    version="2.1",
    description="Unified API using FusionEngine for XGBoost + Autoencoder inference."
)


# ---------------------------------------------------
# REQUEST MODEL
# ---------------------------------------------------
class FeatureInput(BaseModel):
    features: List[float]


# ---------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "fusion_engine": "loaded",
        "models": {
            "xgb": str(type(FusionEngine.__dict__["__wrapped__"].__closure__ if False else "")),
        }
    }


# ---------------------------------------------------
# PREDICTION ENDPOINT (Real-time)
# ---------------------------------------------------
@app.post("/predict")
def predict_single(data: FeatureInput):
    """
    Accepts a single flow's feature vector and returns:
    - supervised_pred
    - autoencoder_flag
    - reconstruction_error
    - final_decision
    """

    try:
        features = np.array(data.features, dtype=float)
        result = FusionEngine.predict(features)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------
# BATCH PREDICTION (CSV Upload)
# ---------------------------------------------------
@app.post("/batch_predict")
async def batch_predict(file: UploadFile = File(...)):
    """
    Accept a CSV containing feature rows.
    Runs fusion prediction on each row.
    """

    # Save CSV temporarily
    temp_path = os.path.join("data", "uploads")
    os.makedirs(temp_path, exist_ok=True)

    file_path = os.path.join(temp_path, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        df = pd.read_csv(file_path).select_dtypes(include=["number"])

        # Convert to numpy
        batch_arr = df.values
        results = FusionEngine.batch_predict(batch_arr)

        return {
            "rows": len(results),
            "results": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
