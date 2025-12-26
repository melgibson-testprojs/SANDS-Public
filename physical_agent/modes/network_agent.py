# physical_agent/modes/network_agent.py

from physical_agent.logical_agents.registry import LogicalAgentRegistry

class NetworkAgent:
    def __init__(self, config, http_client, mqtt_client=None):
        self.config = config
        self.http = http_client
        self.mqtt = mqtt_client

        # ✅ Option B: one registry per physical agent process
        self.logical_registry = LogicalAgentRegistry(
            physical_agent_id=config.agent_id
        )
