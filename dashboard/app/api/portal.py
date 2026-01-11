import uuid
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from dashboard.app.templates_engine import templates

from dashboard.app.services.device_store import device_store
from dashboard.app.services.portal_tokens import portal_token_store

router = APIRouter()

PENDING_TOKENS = {}

@router.get("/portal", response_class=HTMLResponse)
def captive_portal(request: Request):
    return templates.TemplateResponse(
        "portal.html",
        {"request": request}
    )

@router.post("/portal/register")
def register_device(request: Request):
    token = uuid.uuid4().hex
    portal_token_store.create(token)
    return RedirectResponse(
        url=f"/portal/success?token={token}",
        status_code=303
    )


@router.get("/portal/success", response_class=HTMLResponse)
def portal_success(request: Request):
    return templates.TemplateResponse(
        "portal_success.html",
        {"request": request}
    )

@router.get("/portal/pending")
def get_pending_token(request: Request):
    ip = request.client.host
    token = portal_token_store.get_by_ip(ip)
    if not token:
        return {"token": None}
    return {"token": token, "ip" : ip}

@router.get("/portal/pending_all")
def get_all_pending_tokens():
    return {
        "tokens": portal_token_store.list_pending()
    }
