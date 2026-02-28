from fastapi import APIRouter, Depends
from dashboard.app.services.device_store import device_store
from dashboard.app.api.auth import get_current_role
from dashboard.app.services.auth_service import auth_service, UserRole

router = APIRouter(prefix="/api", tags=["Live State"])

@router.get("/state")
async def live_state(role: UserRole = Depends(get_current_role)):
    devices = device_store.all()
    if role:
        devices = auth_service.apply_masking(devices, role)
    return {
        "devices": devices
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
