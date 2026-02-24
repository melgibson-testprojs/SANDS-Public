import time
import math

class VoteStore:
    def __init__(self, quorum_ratio=0.6, window=10):
        self.votes = {}  # target_id -> {voters, first_seen, target_type}
        self.quorum_ratio = quorum_ratio
        self.window = window

    def add_vote(self, target_id, voter, total_agents, target_type):
        now = time.time()

        if target_id not in self.votes:
            self.votes[target_id] = {
                "voters": set(),
                "first_seen": now,
                "target_type": target_type
            }

        self.votes[target_id]["voters"].add(voter)

        return self._check_quorum(target_id, total_agents)

    def _check_quorum(self, target_id, total_agents):
        entry = self.votes[target_id]
        count = len(entry["voters"])
        required = math.ceil(total_agents * self.quorum_ratio)

        if count >= required:
            return True
        return False

    def cleanup(self):
        now = time.time()
        expired = [
            k for k, v in self.votes.items()
            if now - v["first_seen"] > self.window
        ]
        for k in expired:
            del self.votes[k]
    
    def get_vote_count(self, target_id):
        entry = self.votes.get(target_id)
        if not entry:
            return 0
        return len(entry["voters"])
    
    def clear_votes(self, target_id):
        self.votes.pop(target_id, None)