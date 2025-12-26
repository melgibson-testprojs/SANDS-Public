from logical_agents.logical_agent import (
    LogicalAgent,
    generate_logical_agent_id
)


class LogicalAgentRegistry:
    def __init__(self, physical_agent_id: str):
        self.physical_agent_id = physical_agent_id
        self._agents: dict[str, LogicalAgent] = {}

    def get_or_create(self, src_ip: str, mac: str | None = None) -> LogicalAgent:
        logical_id = generate_logical_agent_id(
            self.physical_agent_id,
            src_ip,
            mac
        )

        if logical_id not in self._agents:
            agent = LogicalAgent(
                logical_agent_id=logical_id,
                src_ip=src_ip,
                mac=mac
            )
            self._agents[logical_id] = agent

            print(
                f"[LOGICAL_AGENT_CREATED] "
                f"id={logical_id} ip={src_ip} mac={mac}"
            )

        agent = self._agents[logical_id]
        agent.update_last_seen()
        return agent

    def all_agents(self):
        return list(self._agents.values())
