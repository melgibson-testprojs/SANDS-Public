from agent.core.logical_agents.registry import DeviceState

def decide_action(risk_engine, current_state):
    if risk_engine.should_block():
        return DeviceState.BLOCKED

    if risk_engine.should_quarantine():
        return DeviceState.BLOCKED   # later: QUARANTINED state

    return current_state
