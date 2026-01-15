from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from dashboard.app.templates_engine import templates
from dashboard.app.services.device_store import device_store
from dashboard.app.services.prediction_store import prediction_store
import time

router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    devices = device_store.all()
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "devices": devices
        }
    )

@router.get("/soc/{device_key}", response_class=HTMLResponse)
def soc_view(request: Request, device_key: str):
    device = device_store.get(device_key)
    if not device:
        return HTMLResponse("Device not found", status_code=404)

    return templates.TemplateResponse(
        "soc_device.html",
        {"request": request, "device": device}
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
def topology_view(request: Request):
    return templates.TemplateResponse(
        "topology.html",
        {"request": request}
    )

