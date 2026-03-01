from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any
import time

from dashboard.app.services.mqtt_service import mqtt_service
from dashboard.app.services.prediction_store import prediction_store
from dashboard.app.services.device_store import device_store

router = APIRouter(prefix="/api/debug", tags=["Debug"])

class DebugTrigger(BaseModel):
    action: str
    target_id: Optional[str] = None
    payload: Optional[dict] = None

@router.post("/trigger")
async def trigger_debug_action(trigger: DebugTrigger):
    action = trigger.action
    target_id = trigger.target_id
    
    if action == "ml_detection":
        # Mock a prediction event in the dashboard store
        device_key = target_id or "debug-device"
        decision = trigger.payload.get("decision", "SUSPICIOUS")
        score = float(trigger.payload.get("score", 0.5))
        
        prediction_store.add(
            device_key=device_key,
            decision=decision,
            score=score,
            source="debug_mock",
            extra={"manual_trigger": True}
        )

        lid = device_key
        if device_key.startswith("mac:"):
            mac = device_key[4:]
            import hashlib
            lid = hashlib.sha256(mac.encode()).hexdigest()[:16]

        code = "MAL_CONFIRMED" if decision == "ATTACK" else "ANOM_BEHAV"
        swarm_score = 50.0 if decision == "ATTACK" else 10.0
        mqtt_service.trigger_swarm_alert(lid, code, swarm_score, src="debug_mock_ml")
        
        return {"status": "ok", "message": f"Injected {decision} prediction for {device_key} (lid:{lid}) and notified swarm"}

    elif action == "swarm_alert":
        if not target_id:
            raise HTTPException(status_code=400, detail="target_id required for swarm_alert")
        
        code = trigger.payload.get("code", "ANOM_BEHAV")
        score = float(trigger.payload.get("score", 10.0))

        lid = target_id
        if target_id.startswith("mac:"):
            mac = target_id[4:]
            import hashlib
            lid = hashlib.sha256(mac.encode()).hexdigest()[:16]
        
        success = mqtt_service.trigger_swarm_alert(lid, code, score)
        return {"status": "ok" if success else "error", "message": "Published swarm alert"}

    elif action == "vote_request":
        if not target_id:
            raise HTTPException(status_code=400, detail="target_id required for vote_request")
        
        target_type = trigger.payload.get("target_type", "device")
        success = mqtt_service.trigger_vote_request(target_id, target_type)
        return {"status": "ok" if success else "error", "message": "Published vote request"}

    elif action == "consensus":
        if not target_id:
            raise HTTPException(status_code=400, detail="target_id required for consensus")
        
        target_type = trigger.payload.get("target_type", "device")
        consensus_action = trigger.payload.get("action", "BLOCK")
        success = mqtt_service.trigger_consensus(target_id, target_type, consensus_action)
        return {"status": "ok" if success else "error", "message": "Published consensus message"}

    elif action == "mock_register":
        # Mock a new device in the dashboard
        mock_id = f"mock-agent-{int(time.time() % 1000)}"
        device_store.register(
            agent_id=mock_id,
            mac=trigger.payload.get("mac", "00:00:00:00:00:00"),
            ip=trigger.payload.get("ip", "127.0.0.1")
        )
        return {"status": "ok", "device_id": mock_id}

    elif action == "reset_risk":
        # This is harder without a direct link to the agent's risk engine,
        # but we can reset the dashboard's view if needed.
        # For now, just a placeholder.
        return {"status": "ok", "message": "Reset request logged"}

    else:
        raise HTTPException(status_code=400, detail=f"Unknown debug action: {action}")
