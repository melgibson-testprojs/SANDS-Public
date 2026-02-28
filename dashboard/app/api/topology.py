from fastapi import APIRouter, Depends
from dashboard.app.services.device_store import device_store
from dashboard.app.api.auth import get_current_role
from dashboard.app.services.auth_service import auth_service, UserRole

router = APIRouter(prefix="/api", tags=["Topology"])


@router.get("/topology")
def get_topology(role: UserRole = Depends(get_current_role)):
    nodes = []
    edges = []

    physical_agents = set()

    # ---- Logical agents ----
    for device_id, device in device_store.devices.items():
        agent_id = device.get("agent_id")

        nodes.append({
            "id": device_id,
            "type": "logical",
            "status": device.get("status", "online"),
            "approved": device.get("approved", False),
            "ip": device.get("ip"),
            "mac": device.get("mac"),
            "risk": device.get("risk", 0.0),
        })

        # Edges from all discoverers
        discoverers = device.get("discoverers", [])
        if not discoverers and agent_id:
            discoverers = [agent_id]
            
        for d_id in discoverers:
            physical_agents.add(d_id)
            edges.append({
                "from": d_id,
                "to": device_id,
                "relation": "hosts"
            })

    # ---- Physical agents ----
    import time
    now = time.time()
    for agent_id, agent_info in device_store.agents.items():
        # Only show agents seen in last 2 minutes
        if now - agent_info["last_seen"] < 120:
            nodes.append({
                "id": agent_id,
                "type": "physical",
                "status": "online",
                "risk": 0.0
            })

    result = {
        "nodes": nodes,
        "edges": edges
    }

    if role:
        # We need a special helper for nodes/edges because "from"/"to"/"id" are important
        if role == UserRole.VIEWER:
            for node in result["nodes"]:
                if node["type"] == "logical":
                    node["id"] = auth_service.get_secure_id(node["id"])
                    node["ip"] = auth_service.mask_ip(node["ip"])
                    node["mac"] = auth_service.mask_mac(node["mac"])
            
            for edge in result["edges"]:
                # only resolve logical target
                edge["to"] = auth_service.get_secure_id(edge["to"])

    return result
