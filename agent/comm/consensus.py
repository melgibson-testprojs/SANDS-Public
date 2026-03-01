import time
import math

class VoteStore:
    def __init__(self, quorum_ratio=0.6, window=10):
        self.votes = {}  # target_id -> {voters, first_seen, target_type}
        self.quorum_ratio = quorum_ratio
        self.window = window

    def add_vote(self, target_id, voter, total_agents, target_type, decision="BLOCK"):
        now = time.time()

        if target_id not in self.votes:
            self.votes[target_id] = {
                "voters": {},
                "first_seen": now,
                "target_type": target_type
            }

        self.votes[target_id]["voters"][voter] = decision

        return self._check_quorum(target_id, total_agents)

    def _check_quorum(self, target_id, total_agents):
        entry = self.votes[target_id]
        block_count = sum(1 for d in entry["voters"].values() if d == "BLOCK")
        required = math.ceil(total_agents * self.quorum_ratio)

        if block_count >= required:
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
        return sum(1 for d in entry["voters"].values() if d == "BLOCK")

    def get_vote_breakdown(self, target_id):
        entry = self.votes.get(target_id)
        if not entry:
            return {"BLOCK": 0, "ABSTAIN": 0, "ALLOW": 0}
        
        breakdown = {"BLOCK": 0, "ABSTAIN": 0, "ALLOW": 0}
        for d in entry["voters"].values():
            if d in breakdown:
                breakdown[d] += 1
            else:
                breakdown[d] = 1
        return breakdown
    
    def clear_votes(self, target_id):
        self.votes.pop(target_id, None)