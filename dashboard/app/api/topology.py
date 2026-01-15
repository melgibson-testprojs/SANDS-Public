# dashboard/app/api/topology.py
from fastapi import APIRouter
from dashboard.app.services.device_store import device_store

router = APIRouter(prefix="/api", tags=["Topology"])


@router.get("/topology")
def get_topology():
    nodes = []
    edges = []

    physical_agents = set()

    # ---- Logical agents ----
    for device_id, device in device_store.devices.items():
        agent_id = device.get("agent_id")

        nodes.append({
            "id": device_id,
            "type": "logical",
            "state": device.get("state", "NEW"),
            "ip": device.get("ip"),
            "mac": device.get("mac"),
            "risk": device.get("risk", 0.0),
        })

        if agent_id:
            physical_agents.add(agent_id)
            edges.append({
                "from": agent_id,
                "to": device_id,
                "relation": "hosts"
            })

    # ---- Physical agents ----
    for agent_id in physical_agents:
        nodes.append({
            "id": agent_id,
            "type": "physical",
            "state": "ONLINE"
        })

    return {
        "nodes": nodes,
        "edges": edges
    }
