import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dashboard.app.services.log_aggregator import log_aggregator
import json

def test_aggregator():
    print(f"Logs directory: {log_aggregator.logs_dir}")
    print(f"Exists: {os.path.exists(log_aggregator.logs_dir)}")
    
    events = log_aggregator.get_all_events()
    print(f"Total events found: {len(events)}")
    
    if events:
        print("\nSample Event:")
        print(json.dumps(events[0], indent=2))
        
        # Check for different sources
        sources = set(e["source"] for e in events)
        print(f"\nSources found: {sources}")
        
        # Check for categories
        categories = set(e["category"] for e in events)
        print(f"Categories found: {categories}")

if __name__ == "__main__":
    test_aggregator()
