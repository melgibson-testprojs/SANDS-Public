import sys
import os
import asyncio
from unittest.mock import MagicMock

# Mock Groq to avoid ModuleNotFoundError in environments without it
sys.modules["groq"] = MagicMock()

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dashboard.app.services.xai_service import xai_service
from dashboard.app.services.log_aggregator import log_aggregator

async def test_optimization():
    print("Testing Keyword-Based Context Optimization...")
    
    # 1. Test with a specific LID
    test_lid = "c21f885fb8fd9700"
    print(f"\n--- Scenario 1: Searching for LID: {test_lid} ---")
    context = xai_service._prepare_context(f"What happened to LID {test_lid}?")
    print(f"Context Length (lines): {len(context.splitlines())}")
    if test_lid in context.lower():
        print("SUCCESS: Target LID found in context.")
    else:
        print("WARNING: Target LID not found in context (might not be in logs).")

    # 2. Test with an Agent ID
    test_agent = "agent-local-001"
    print(f"\n--- Scenario 2: Searching for Agent: {test_agent} ---")
    context = xai_service._prepare_context(f"Is {test_agent} online?")
    print(f"Context Length (lines): {len(context.splitlines())}")
    if test_agent in context.lower():
        print("SUCCESS: Target Agent found in context.")
    else:
        print("WARNING: Target Agent not found in context.")

    # 3. Test with a general security keyword
    print(f"\n--- Scenario 3: Searching for 'attack' ---")
    context = xai_service._prepare_context("Show me any recent attacks.")
    print(f"Context Length (lines): {len(context.splitlines())}")
    if "attack" in context.lower():
        print("SUCCESS: 'attack' context found.")
    else:
        print("NOTE: 'attack' not found (might not be any attack logs).")

    # 4. Verify line count limit
    print(f"\n--- Scenario 4: Verifying Hard Limit (40) ---")
    context = xai_service._prepare_context("Give me everything.")
    lines = context.splitlines()
    print(f"Total lines returned: {len(lines)}")
    if len(lines) <= 40:
        print("SUCCESS: Context is within the 40-line limit.")
    else:
        print(f"FAILURE: Context exceeds limit ({len(lines)} lines).")

if __name__ == "__main__":
    asyncio.run(test_optimization())
