from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from dashboard.app.services.device_store import device_store

router = APIRouter()
templates = Jinja2Templates(directory="dashboard/app/templates")

@router.get("/portal", response_class=HTMLResponse)
def captive_portal(request: Request):
    return templates.TemplateResponse(
        "portal.html",
        {"request": request}
    )

@router.post("/portal/register")
def register_device(request: Request):
    device_store.register(ip=request.client.host)
    return RedirectResponse(url="/portal/success", status_code=303)

@router.get("/portal/success", response_class=HTMLResponse)
def portal_success(request: Request):
    return templates.TemplateResponse(
        "portal_success.html",
        {"request": request}
    )