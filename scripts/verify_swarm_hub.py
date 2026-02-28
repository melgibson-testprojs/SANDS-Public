import os
import sys
from datetime import datetime
import time

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dashboard.app.services.log_aggregator import log_aggregator

def test_swarm_summary_hub():
    log_file = log_aggregator.agent_log
    
    # 1. Simulate an ACTIVE swarm lifecycle
    target_active = f"target-active-{int(time.time())}"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S,000")
    
    mock_active = [
        f"{ts} | INFO | NetworkAgent | VOTE_REQ_SENT | target={target_active} | type=device",
        f"{ts} | INFO | NetworkAgent | VOTE_CAST_RECEIVED | voter=agent-001 | target={target_active} | votes=1/3 | quorum=2"
    ]
    
    # 2. Simulate a COMPLETED swarm lifecycle
    target_done = f"target-done-{int(time.time())}"
    mock_done = [
        f"{ts} | INFO | NetworkAgent | VOTE_REQ_SENT | target={target_done} | type=device",
        f"{ts} | INFO | NetworkAgent | VOTE_CAST_RECEIVED | voter=agent-001 | target={target_done} | votes=1/2 | quorum=2",
        f"{ts} | INFO | NetworkAgent | VOTE_CAST_RECEIVED | voter=agent-002 | target={target_done} | votes=2/2 | quorum=2",
        f"{ts} | WARNING | NetworkAgent | CONSENSUS_REACHED | leader=agent-001 | target={target_done} | votes>=2 | decision=BLOCK",
        f"{ts} | WARNING | NetworkAgent | CONSENSUS_APPLIED | decided_by=agent-001 | target={target_done} | type=device | action=BLOCK"
    ]
    
    print(f"Injecting mock events for {target_active} and {target_done}...")
    with open(log_file, "a") as f:
        for line in mock_active + mock_done:
            f.write(line + "\n")
            
    print("Verification: Check the Incident View page for the new Swarm Hub.")

if __name__ == "__main__":
    test_swarm_summary_hub()
