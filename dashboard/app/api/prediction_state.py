from fastapi import APIRouter
from dashboard.app.services.prediction_store import prediction_store

from dashboard.app.services.auth_service import auth_service

router = APIRouter(prefix="/api", tags=["Prediction State"])

@router.get("/predictions/{device_key}")
def get_predictions(device_key: str):
    real_key = auth_service.resolve_id(device_key)
    return {
        "predictions": prediction_store.get(real_key)
    }
