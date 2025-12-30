from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from dashboard.app.templates_engine import templates
from dashboard.app.services.device_store import device_store

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