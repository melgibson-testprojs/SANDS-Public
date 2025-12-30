from fastapi import APIRouter
from dashboard.app.services.device_store import device_store

router = APIRouter(prefix="/api", tags=["Live State"])

@router.get("/state")
def live_state():
    return {
        "devices": device_store.all()
    }