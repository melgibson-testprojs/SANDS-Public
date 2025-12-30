from fastapi import APIRouter, Request
from pydantic import BaseModel

from dashboard.app.services.device_store import device_store

router = APIRouter()

class AgentHello(BaseModel):
    agent_id: str
    mac: str | None = None

class Heartbeat(BaseModel):
    agent_id: str

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
