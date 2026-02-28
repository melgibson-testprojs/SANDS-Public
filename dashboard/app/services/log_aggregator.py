import os
import re
from datetime import datetime
from typing import List, Dict, Any

class LogAggregator:
    def __init__(self, logs_dir: str):
        self.logs_dir = logs_dir
        self.agent_log = os.path.join(logs_dir, "swarmsec_agent.log")
        self.ids_log = os.path.join(logs_dir, "swarmsec_ids.log")
        self.server_log = os.path.join(logs_dir, "swarmsec_server.log")

    def get_all_events(self) -> List[Dict[str, Any]]:
        events = []
        events.extend(self._parse_agent_log())
        events.extend(self._parse_ids_log())
        events.extend(self._parse_server_log())
        
        # Sort by timestamp descending
        events.sort(key=lambda x: x["timestamp"], reverse=True)
        return events

    def _parse_agent_log(self) -> List[Dict[str, Any]]:
        events = []
        if not os.path.exists(self.agent_log):
            return events

        # Regex for standard log format: 2026-01-11 11:56:46,572 | INFO | run_agent | Message
        pattern = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \| (\w+) \| ([\w\.-]+) \| (.*)$")

        # Specific logs to include as requested
        # LOGICAL_AGENT_CREATED, PORTAL_BIND_SUCCESS, MQTT, SWARM_STATUS, ML_SUSPICIOUS_TRIGGERED,
        # RISK_UPDATE, MODEL_ASSIGNED, SWARM_ALERT, VOTE_REQUEST_RECEIVED, VOTE_REQ_SENT, 
        # VOTE_CAST_RECEIVED, CONSENSUS_APPLIED
        allowed_types = {
            "LOGICAL_AGENT_CREATED", "PORTAL_BIND_SUCCESS", "SWARM_STATUS", 
            "ML_SUSPICIOUS_TRIGGERED", "RISK_UPDATE", "MODEL_ASSIGNED", 
            "SWARM_ALERT", "VOTE_REQUEST_RECEIVED", "VOTE_REQ_SENT", 
            "VOTE_CAST_RECEIVED", "CONSENSUS_APPLIED", "CONSENSUS_REACHED",
            "SWARM_COMMAND"
        }
        
        discard_components = {"arp_monitor"}
        discard_messages = {"FLOW ACCEPTED", "FLOW DROPPED", "Starting NetworkAgent", "Agent successfully registered"}

        try:
            with open(self.agent_log, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    match = pattern.match(line.strip())
                    if match:
                        ts_str, severity, component, message = match.groups()
                        
                        if component in discard_components:
                            continue

                        # Check if message contains discarded substrings
                        if any(dm in message for dm in discard_messages):
                            continue

                        event = {
                            "timestamp": ts_str,
                            "source": "agent",
                            "category": "System",
                            "severity": severity,
                            "description": message,
                            "metadata": {"component": component}
                        }

                        # Refine category and extract metadata for specific patterns
                        if "|" in message:
                            parts = [p.strip() for p in message.split("|")]
                            event_type = parts[0]
                            
                            # Filter by event type if it looks like a formal event
                            if event_type.isupper() and "_" in event_type or event_type in allowed_types:
                                if event_type not in allowed_types and "MQTT" not in event_type.upper():
                                    continue
                            
                            # Extract key-value pairs
                            for part in parts[1:]:
                                if "=" in part:
                                    k_v = part.split("=", 1)
                                    if len(k_v) == 2:
                                        k, v = k_v
                                        event["metadata"][k.strip()] = v.strip()
                            
                            event["category"] = self._detect_category(event_type, event["metadata"])
                        
                        # Special handling for MQTT which might be in the description/message directly
                        is_mqtt = "MQTT" in message.upper()
                        is_allowed = False
                        
                        if "|" in message:
                            event_type = message.split("|")[0].strip()
                            if event_type in allowed_types:
                                is_allowed = True
                        
                        if is_allowed or is_mqtt or severity in ["ERROR", "CRITICAL"]:
                            events.append(event)
                            
        except Exception as e:
            print(f"Error parsing agent log: {e}")
            
        return events

    def _parse_ids_log(self) -> List[Dict[str, Any]]:
        events = []
        if not os.path.exists(self.ids_log):
            return events

        # Format: 2026-01-11 11:57:27,730 | INFO | AGENT=agent-local-001 | LID=c21f885fb8fd9700 | ...
        pattern = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \| (\w+) \| (.*)$")

        try:
            with open(self.ids_log, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    match = pattern.match(line.strip())
                    if match:
                        ts_str, severity, message = match.groups()
                        
                        # IDS logs often contain FLOW ACCEPTED/DROPPED which user wants to discard
                        if "FLOW ACCEPTED" in message or "FLOW DROPPED" in message:
                            continue

                        event = {
                            "timestamp": ts_str,
                            "source": "ids",
                            "category": "Detection",
                            "severity": severity,
                            "description": "Network traffic detection",
                            "metadata": {}
                        }

                        if "|" in message:
                            parts = [p.strip() for p in message.split("|")]
                            for part in parts:
                                if "=" in part:
                                    k, v = part.split("=", 1)
                                    event["metadata"][k.strip()] = v.strip()
                            
                            # Construct a better description if available
                            if "DECISION" in event["metadata"]:
                                decision = event["metadata"]["DECISION"]
                                # User wants to discard flow accepted and dropped
                                if decision in ["ACCEPTED", "DROPPED"]:
                                    continue
                                    
                                event["description"] = f"Flow {decision} (LID: {event['metadata'].get('LID', 'N/A')})"
                                if decision == "SUSPICIOUS":
                                    event["severity"] = "WARNING"
                                elif decision == "ATTACK":
                                    event["severity"] = "CRITICAL"

                        events.append(event)
        except Exception as e:
            print(f"Error parsing ids log: {e}")

        return events

    def _parse_server_log(self) -> List[Dict[str, Any]]:
        events = []
        if not os.path.exists(self.server_log):
            return events

        # Example: 2026-02-27 15:10:05,123 | INFO | server | Message
        pattern = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \| (\w+) \| ([\w\.-]+) \| (.*)$")

        try:
            with open(self.server_log, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    match = pattern.match(line.strip())
                    if match:
                        ts_str, severity, component, message = match.groups()
                        
                        # Discard startup noise
                        if "Started server" in message or "Uvicorn running" in message:
                            continue

                        events.append({
                            "timestamp": ts_str,
                            "source": "server",
                            "category": "System",
                            "severity": severity,
                            "description": message,
                            "metadata": {"component": component}
                        })
        except Exception as e:
            print(f"Error parsing server log: {e}")

        return events

    def _detect_category(self, event_type: str, metadata: Dict[str, Any]) -> str:
        swarm_types = ["VOTE_REQ_SENT", "VOTE_CAST_RECEIVED", "CONSENSUS_REACHED", "CONSENSUS_APPLIED", "SWARM_ALERT", "SWARM_COMMAND", "SWARM_STATUS", "SWARM_HELLO_SENT", "VOTE_REQUEST_RECEIVED", "VOTE_CAST_SENT"]
        network_types = ["LOGICAL_AGENT_CREATED", "FLOW ACCEPTED", "FLOW DROPPED", "PORTAL_BIND_SUCCESS", "PORTAL_BIND_FAILED", "DEVICE_STATE_CHANGE", "DEVICE_MANUAL_ALLOW"]
        
        if event_type in swarm_types or "swarm" in event_type.lower():
            return "Swarm"
        if event_type in network_types:
            return "Network"
        if "ERROR" in event_type or "FAILED" in event_type or "MQTT" in event_type.upper():
            return "Error"
        return "System"

# Path relative to this file: ../app/services -> ../app -> ../ -> root -> logs
LOGS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "logs"))
log_aggregator = LogAggregator(LOGS_DIR)

# Path relative to this file: ../app/services -> ../app -> ../ -> root -> logs
LOGS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "logs"))
log_aggregator = LogAggregator(LOGS_DIR)
