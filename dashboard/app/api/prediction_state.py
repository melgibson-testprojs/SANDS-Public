from fastapi import APIRouter
from dashboard.app.services.prediction_store import prediction_store

router = APIRouter(prefix="/api", tags=["Prediction State"])

@router.get("/predictions/{device_key}")
def get_predictions(device_key: str):
    return {
        "predictions": prediction_store.get(device_key)
    }
