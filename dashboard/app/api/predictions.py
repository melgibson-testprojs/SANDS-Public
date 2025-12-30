from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from dashboard.app.services.prediction_store import prediction_store

router = APIRouter(tags=["Predictions"])

class PredictionIn(BaseModel):
    device_key: str
    decision: str
    score: float
    source: str
    extra: Optional[dict] = None

@router.post("/agent/predict")
def ingest_prediction(p: PredictionIn):
    prediction_store.add(
        device_key=p.device_key,
        decision=p.decision,
        score=p.score,
        source=p.source,
        extra=p.extra
    )
    return {"status": "ok"}
