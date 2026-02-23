import hashlib

class LeaderElection:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.known_agents = set([agent_id])

    def register_agent(self, agent_id: str):
        self.known_agents.add(agent_id)

    def compute_leader(self) -> str:
        return sorted(self.known_agents)[0]

    def is_leader(self) -> bool:
        return self.agent_id == self.compute_leader()