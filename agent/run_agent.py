#!/usr/bin/env python3
"""
Entrypoint for the SwarmSec Network Agent.

Note: imports use package-qualified names (agent.core, agent.comm, etc.)
Run from the project root (Phase2.1) as:
    python -m agent.run_agent --server http://localhost:8000 --agent-id agent-01
"""
import argparse
import os
import sys
from agent.core.config import config
from agent.core.logger import get_logger
from agent.comm.http_client import HTTPClient
from agent.comm.mqtt_client import MQTTClient
from agent.modes.network_agent import NetworkAgent

logger = get_logger("run_agent")


def parse_args():
    p = argparse.ArgumentParser(prog="run_agent.py")
    p.add_argument("--server", "-s", default=config.server_url, help="Fusion server base URL (http://host:port)")
    p.add_argument("--agent-id", "-a", default=config.agent_id, help="Agent unique id")
    p.add_argument("--poll", "-p", type=float, default=config.polling_interval, help="Polling interval (seconds)")
    p.add_argument("--mqtt", default=config.mqtt_broker, help="MQTT broker hostname")
    p.add_argument("--mqtt-port", type=int, default=config.mqtt_port, help="MQTT broker port")
    p.add_argument("--pcap", default=None, help="Optional path to a pcap file for flow ingestion (requires scapy)")
    p.add_argument("--debug-feature-names", action="store_true", help="Attach feature names in telemetry payload (debug only)")
    p.add_argument("--no-mqtt", action="store_true", help="Disable MQTT client (use HTTP only)")
    return p.parse_args()


def main():
    args = parse_args()

    # Apply CLI args to config
    config.server_url = args.server
    config.agent_id = args.agent_id
    config.polling_interval = args.poll
    config.mqtt_broker = args.mqtt
    config.mqtt_port = args.mqtt_port

    # propagate debug flag via environment variable expected by network_agent
    if args.debug_feature_names:
        os.environ["DEBUG_FEATURE_NAMES"] = "1"
    else:
        os.environ.pop("DEBUG_FEATURE_NAMES", None)

    # Set PCAP_PATH environment if provided (NetworkAgent reads it)
    if args.pcap:
        if not os.path.exists(args.pcap):
            logger.error(f"PCAP path not found: {args.pcap}")
            sys.exit(2)
        os.environ["PCAP_PATH"] = args.pcap
        logger.info(f"PCAP mode enabled: {args.pcap}")
    else:
        os.environ.pop("PCAP_PATH", None)

    # HTTP client (used for register/heartbeat/telemetry)
    http = HTTPClient(config.server_url, token=config.token)

    # MQTT client (optional)
    mqtt = None
    if not args.no_mqtt:
        try:
            mqtt = MQTTClient(config.mqtt_broker, config.mqtt_port, token=config.token)
            mqtt.connect()
        except Exception as e:
            logger.error(f"MQTT client failed to start: {e}. Continuing without MQTT.")
            mqtt = None
    else:
        logger.info("MQTT disabled by CLI (HTTP-only mode).")

    agent = NetworkAgent(config, http, mqtt)

    # Run main loop
    try:
        agent.run()
    except KeyboardInterrupt:
        logger.info("Agent stopped by user (KeyboardInterrupt).")
    except Exception as e:
        logger.exception(f"Unhandled exception in agent: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
