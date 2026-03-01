# server/main.py

from fastapi import FastAPI, HTTPException, File, UploadFile
from pydantic import BaseModel
from typing import List, Dict, Optional

import numpy as np
import pandas as pd
import os
import shutil
import time
import joblib

import threading
from fusion.fusion_engine import FusionEngine
from agent.utils.cic_feature_extractor import FEATURE_NAMES
from server.logger import get_ids_logger, get_server_logger
from server.event_emitter import emit_prediction_event
from server.training.flow_logger import log_flow_for_training
from server.scheduler import scheduler_loop

# ---------------------------------------------------
# LOGGER
# ---------------------------------------------------

ids_logger = get_ids_logger()        # prediction only
server_logger = get_server_logger()  # everything else


# ---------------------------------------------------
# LOAD SCALER
# ---------------------------------------------------

SCALER_PATH = os.path.join("models", "scaler.pkl")

if not os.path.exists(SCALER_PATH):
    raise RuntimeError(f"Scaler not found at {SCALER_PATH}")

SCALER = joblib.load(SCALER_PATH)

EXPECTED_FEATURE_COUNT = len(FEATURE_NAMES)

# ---------------------------------------------------
# AUTOENCODER MODEL DISCOVERY + ROTATION
# ---------------------------------------------------

BASE_AE_PATH = os.path.join("models", "autoencoder_cicids2018.h5")
AE_EXPERIMENTS_DIR = os.path.join("models", "experiments", "ae")

MODEL_ASSIGNMENTS: Dict[str, str] = {}
MODEL_ROTATION_COUNTER = 0


def discover_autoencoders():
    models = []

    # Base model first
    if os.path.exists(BASE_AE_PATH):
        models.append(("base", BASE_AE_PATH))

    # Incremental runs
    if os.path.exists(AE_EXPERIMENTS_DIR):
        def extract_run_number(name):
            try:
                return int(name.split("_")[1])
            except:
                return 0

        runs = sorted(
            os.listdir(AE_EXPERIMENTS_DIR),
            key=extract_run_number,
            reverse=False   # oldest first (ascending)
        )
        
        for run in runs:
            model_path = os.path.join(AE_EXPERIMENTS_DIR, run, "autoencoder.h5")
            if os.path.exists(model_path):
                models.append((run, model_path))

    return models


AVAILABLE_AE_MODELS = discover_autoencoders()

if not AVAILABLE_AE_MODELS:
    raise RuntimeError("No autoencoder models found.")

# ---------------------------------------------------
# APP
# ---------------------------------------------------

app = FastAPI(
    title="SwarmSec IDS Server",
    version="2.1",
    description="Unified API using FusionEngine for XGBoost + Autoencoder inference."
)

# ---------------------------------------------------
# IN-MEMORY AGENT REGISTRY (D1)
# ---------------------------------------------------

AGENTS: Dict[str, dict] = {}

# ---------------------------------------------------
# REQUEST MODELS
# ---------------------------------------------------

class FeatureInput(BaseModel):
    features: List[float]


class RegisterRequest(BaseModel):
    agent_id: str
    capabilities: List[str] = []


class RegisterResponse(BaseModel):
    agent_id: str
    token: str
    model_version: str
    model_path: str


class HeartbeatRequest(BaseModel):
    agent_id: str
    state: str
    ts: float


class TelemetryRequest(BaseModel):
    agent_id: str
    logical_agent_id: Optional[str] = None
    ts: float
    features: List[float]
    flow_meta: Optional[dict] = None

# ---------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "fusion_engine": "loaded",
        "registered_agents": len(AGENTS)
    }

@app.on_event("startup")
def start_scheduler():
    t = threading.Thread(target=scheduler_loop, daemon=True)
    t.start()
# ---------------------------------------------------
# AGENT REGISTRATION (D1)
# ---------------------------------------------------

@app.post("/register", response_model=RegisterResponse)
def register_agent(req: RegisterRequest):
    global MODEL_ROTATION_COUNTER

    token = f"token-{req.agent_id}"

    # If already assigned → return same version
    if req.agent_id in MODEL_ASSIGNMENTS:
        model_version = MODEL_ASSIGNMENTS[req.agent_id]
    else:
        index = MODEL_ROTATION_COUNTER % len(AVAILABLE_AE_MODELS)
        model_version, _ = AVAILABLE_AE_MODELS[index]

        MODEL_ASSIGNMENTS[req.agent_id] = model_version
        MODEL_ROTATION_COUNTER += 1

    # Resolve model path
    model_path = None
    for version, path in AVAILABLE_AE_MODELS:
        if version == model_version:
            model_path = path
            break

    AGENTS[req.agent_id] = {
        "capabilities": req.capabilities,
        "token": token,
        "state": "REGISTERED",
        "last_seen": time.time(),
        "model_version": model_version
    }

    server_logger.info(
        f"MODEL_ASSIGNED | agent={req.agent_id} | version={model_version}"
    )

    return {
        "agent_id": req.agent_id,
        "token": token,
        "model_version": model_version,
        "model_path": model_path
    }

# ---------------------------------------------------
# AGENT HEARTBEAT (D1)
# ---------------------------------------------------

@app.post("/heartbeat")
def heartbeat(req: HeartbeatRequest):
    agent = AGENTS.get(req.agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not registered")

    agent["state"] = req.state
    agent["last_seen"] = req.ts

    return {"status": "ok"}

# ---------------------------------------------------
# AGENT TELEMETRY (D2 → ML)
# ---------------------------------------------------

@app.post("/telemetry")
def telemetry(req: TelemetryRequest):
    agent = AGENTS.get(req.agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not registered")

    # --- HARD VALIDATION ---
    if len(req.features) != EXPECTED_FEATURE_COUNT:
        raise HTTPException(
            status_code=400,
            detail=f"Expected {EXPECTED_FEATURE_COUNT} features, got {len(req.features)}"
        )

    # --- SCALE FEATURES SAFELY ---
    features_df = pd.DataFrame([req.features], columns=FEATURE_NAMES)
    features_scaled = SCALER.transform(features_df)

    # Convert to 1D vector for FusionEngine
    features_vector = features_scaled[0]

    # --- ML INFERENCE ---
    model_version = agent.get("model_version", "base")

    result = FusionEngine.predict(
        features_vector,
        model_version=model_version
    )

    log_flow_for_training(
        features=features_vector,
        result=result,
        agent_id=req.agent_id,
        logical_agent_id=req.logical_agent_id,
    )


    # -------- IDS LOG ENTRY --------
    ids_logger.info(
        f"AGENT={req.agent_id} | "
        f"LID={req.logical_agent_id or 'UNKNOWN'} | "     
        f"MAC={req.flow_meta.get('mac')} | "    
        f"SRC={req.flow_meta.get('src_ip') if req.flow_meta else 'NA'}:"
        f"{req.flow_meta.get('src_port') if req.flow_meta else 'NA'} | "
        f"DST={req.flow_meta.get('dst_ip') if req.flow_meta else 'NA'}:"
        f"{req.flow_meta.get('dst_port') if req.flow_meta else 'NA'} | "
        f"PROTO={req.flow_meta.get('protocol') if req.flow_meta else 'NA'} | "
        f"DECISION={result.get('final_decision')} | "
        f"SUPERVISED={result.get('supervised_pred')} | "
        f"AE_FLAG={result.get('autoencoder_flag')} | "
        f"RECON_ERR={result.get('reconstruction_error')}"
    )

    emit_prediction_event(
        agent_id=req.agent_id,
        fusion_result=result,
        flow_meta=req.flow_meta
    )

    return {
        "agent_id": req.agent_id,
        "prediction": result
    }

# ---------------------------------------------------
# PREDICTION ENDPOINT (UNCHANGED)
# ---------------------------------------------------

@app.post("/predict")
def predict_single(data: FeatureInput):
    try:
        features = np.array(data.features, dtype=float)
        result = FusionEngine.predict(features)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------
# BATCH PREDICTION (UNCHANGED)
# ---------------------------------------------------

@app.post("/batch_predict")
async def batch_predict(file: UploadFile = File(...)):
    temp_path = os.path.join("data", "uploads")
    os.makedirs(temp_path, exist_ok=True)

    file_path = os.path.join(temp_path, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        df = pd.read_csv(file_path).select_dtypes(include=["number"])
        batch_arr = df.values
        results = FusionEngine.batch_predict(batch_arr)

        return {
            "rows": len(results),
            "results": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

