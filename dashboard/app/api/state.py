from fastapi import APIRouter
from dashboard.app.services.device_store import device_store

router = APIRouter(prefix="/api", tags=["Live State"])

@router.get("/state")
def live_state():
    return {
        "devices": device_store.all()
    }

@router.get("/approved_macs")
def approved_macs():
    """
    Returns list of approved MAC addresses.
    """
    approved = []
    for d in device_store.all():
        if d.get("approved") and d.get("mac"):
            approved.append(d["mac"].lower())
    return {
        "approved_macs": approved
    }
