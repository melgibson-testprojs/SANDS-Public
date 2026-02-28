from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from dashboard.app.templates_engine import templates
from dashboard.app.services.device_store import device_store
from dashboard.app.services.prediction_store import prediction_store
from dashboard.app.api.auth import get_current_user, get_current_role
from dashboard.app.services.log_aggregator import log_aggregator
from dashboard.app.services.auth_service import UserRole, auth_service
from dashboard.app.services.xai_service import xai_service
import time

router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_view(request: Request, user = Depends(get_current_user), role = Depends(get_current_role)):
    if not user:
        return RedirectResponse(url="/login")
    devices = device_store.all()
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "devices": devices,
            "user": user,
            "role": role
        }
    )

@router.get("/soc/{device_key}", response_class=HTMLResponse)
async def soc_view(request: Request, device_key: str, user = Depends(get_current_user), role = Depends(get_current_role)):
    if not user:
        return RedirectResponse(url="/login")
    
    real_key = auth_service.resolve_id(device_key)
    device = device_store.get(real_key)
    if not device:
        return HTMLResponse("Device not found", status_code=404)
    
    if role == UserRole.VIEWER:
        device = auth_service.apply_masking(device.copy(), role)

    return templates.TemplateResponse(
        "soc_device.html",
        {"request": request, "device": device, "user": user, "role": role}
    )

@router.get("/dashboard/summary")
def dashboard_summary():
    devices = device_store.all()

    total = len(devices)
    online = sum(1 for d in devices if d["status"] == "online")

    # last 5 minutes
    cutoff = time.time() - 300
    suspicious = 0

    for preds in prediction_store._store.values():
        for p in preds:
            if p["ts"] >= cutoff and p["decision"] != "BENIGN":
                suspicious += 1

    return {
        "total_devices": total,
        "online_devices": online,
        "recent_threats": suspicious,
        "system_status": "OK"
    }

@router.get("/dashboard/decision_breakdown")
def decision_breakdown():
    counts = {
        "BENIGN": 0,
        "SUSPICIOUS": 0,
        "ATTACK": 0
    }

    for preds in prediction_store._store.values():
        for p in preds:
            if p["decision"] in counts:
                counts[p["decision"]] += 1

    return counts

@router.get("/dashboard/events")
def recent_events(limit: int = 20):
    events = []

    for device_key, preds in prediction_store._store.items():
        for p in preds:
            events.append({
                "ts": p["ts"],
                "device": device_key,
                "decision": p["decision"],
                "score": p["score"]
            })

    events.sort(key=lambda x: x["ts"], reverse=True)
    return events[:limit]

@router.get("/dashboard/topology", response_class=HTMLResponse)
async def topology_view(request: Request, user = Depends(get_current_user), role = Depends(get_current_role)):
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(
        "topology.html",
        {"request": request, "user": user, "role": role}
    )

@router.get("/dashboard/models", response_class=HTMLResponse)
async def model_management(request: Request, user = Depends(get_current_user), role = Depends(get_current_role)):
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(
        "model_management.html",
        {"request": request, "user": user, "role": role}
    )

@router.get("/dashboard/incidents", response_class=HTMLResponse)
async def incidents_view(request: Request, user = Depends(get_current_user), role = Depends(get_current_role)):
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(
        "incident_view.html",
        {"request": request, "user": user, "role": role}
    )

@router.get("/dashboard/debug", response_class=HTMLResponse)
async def debug_view(request: Request, user = Depends(get_current_user), role = Depends(get_current_role)):
    if not user:
        return RedirectResponse(url="/login")
    
    # Optional: and only allow admin
    if role != UserRole.ADMIN:
         raise HTTPException(status_code=403, detail="Forbidden")

    return templates.TemplateResponse(
        "debug.html",
        {"request": request, "user": user, "role": role}
    )

@router.get("/api/incidents")
async def get_incidents(role: UserRole = Depends(get_current_role)):
    events = log_aggregator.get_all_events()
    if role:
        events = auth_service.apply_masking(events, role)
    return events

@router.get("/dashboard/xai", response_class=HTMLResponse)
async def xai_view(request: Request, user = Depends(get_current_user), role = Depends(get_current_role)):
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(
        "xai_chat.html",
        {"request": request, "user": user, "role": role}
    )

@router.post("/api/xai/chat")
async def xai_chat(request: Request):
    data = await request.json()
    message = data.get("message")
    history = data.get("history", [])
    
    response = await xai_service.get_response(message, history)
    return {"response": response}
