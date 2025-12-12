from dataclasses import dataclass
import os

@dataclass
class AgentConfig:
    agent_id: str = os.environ.get("AGENT_ID", "agent-local-001")
    server_url: str = os.environ.get("SERVER_URL", "http://localhost:8000")
    mqtt_broker: str = os.environ.get("MQTT_BROKER", "localhost")
    mqtt_port: int = int(os.environ.get("MQTT_PORT", 1883))
    polling_interval: float = float(os.environ.get("POLL_INTERVAL", 2.0))
    token: str = os.environ.get("AGENT_TOKEN", "")

config = AgentConfig()
