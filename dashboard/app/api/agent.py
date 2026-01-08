from fastapi import APIRouter, Request
from pydantic import BaseModel
from enum import Enum

from dashboard.app.services.device_store import device_store
from dashboard.app.services.portal_tokens import portal_token_store
router = APIRouter()

class AgentHello(BaseModel):
    agent_id: str
    mac: str | None = None

class Heartbeat(BaseModel):
    agent_id: str

class AgentBind(BaseModel):
    portal_token: str
    mac: str
    agent_id: str

class DeviceAction(str, Enum):
    allow = "allow"
    block = "block"

@router.post("/agent/hello")
def agent_hello(payload: AgentHello, request: Request):
    device = device_store.register(
        agent_id=payload.agent_id,
        mac=payload.mac,
        ip=request.client.host
    )
    return {"status": "registered", "device": device}

@router.post("/agent/heartbeat")
def agent_heartbeat(payload: Heartbeat, request: Request):
    device_store.heartbeat(
        agent_id=payload.agent_id,
        ip=request.client.host
    )
    return {"status": "ok"}

@router.post("/agent/bind")
def bind_device(payload: AgentBind, request: Request):
    token_data = portal_token_store.consume(payload.portal_token)

    if not token_data:
        return {"status": "invalid_or_expired_token"}

    device = device_store.register(
        mac=payload.mac,
        agent_id=payload.agent_id,
        ip=request.client.host
    )

    device["approved"] = True

    return {
        "status": "approved",
        "device": device
    }

@router.post("/agent/device/{device_key}/{action}")
def device_action(device_key: str, action: DeviceAction):
    device = device_store.get(device_key)
    if not device:
        return {"status": "error", "reason": "device_not_found"}

    if action == DeviceAction.allow:
        device["approved"] = True
        device["status"] = "online"

    elif action == DeviceAction.block:
        device["approved"] = False
        device["status"] = "blocked"

    return {
        "status": "ok",
        "device": device,
        "action": action
    }