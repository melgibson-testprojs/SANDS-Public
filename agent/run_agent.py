#!/usr/bin/env python3
"""
Entrypoint for the SwarmSec Network Agent.

Run from project root (Phase2.1) as:
    python -m agent.run_agent
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


# ---------------------------------------------------------
# CLI ARGUMENTS
# ---------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(prog="run_agent.py")

    # ML backend (Fusion / IDS)
    p.add_argument(
        "--server", "-s",
        default=config.server_url,
        help="ML backend base URL (default: http://localhost:8000)"
    )

    # Agent identity
    p.add_argument(
        "--agent-id", "-a",
        default=config.agent_id,
        help="Physical agent ID"
    )

    # Polling
    p.add_argument(
        "--poll", "-p",
        type=float,
        default=config.polling_interval,
        help="Polling interval (seconds)"
    )

    # MQTT
    p.add_argument("--mqtt", default=config.mqtt_broker)
    p.add_argument("--mqtt-port", type=int, default=config.mqtt_port)
    p.add_argument("--no-mqtt", action="store_true")

    # Optional
    p.add_argument("--pcap", default=None)
    p.add_argument("--debug-feature-names", action="store_true")

    return p.parse_args()


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():
    args = parse_args()

    # ---------------- CONFIG ----------------

    config.server_url = args.server
    config.agent_id = args.agent_id
    config.polling_interval = args.poll
    config.mqtt_broker = args.mqtt
    config.mqtt_port = args.mqtt_port

    logger.info(f"Agent ID        : {config.agent_id}")
    logger.info(f"ML Backend      : {config.server_url}")
    logger.info(f"Dashboard       : {config.dashboard_url}")

    # ---------------- ENV FLAGS ----------------

    if args.debug_feature_names:
        os.environ["DEBUG_FEATURE_NAMES"] = "1"
    else:
        os.environ.pop("DEBUG_FEATURE_NAMES", None)

    if args.pcap:
        if not os.path.exists(args.pcap):
            logger.error(f"PCAP path not found: {args.pcap}")
            sys.exit(2)
        os.environ["PCAP_PATH"] = args.pcap
        logger.info(f"PCAP mode enabled: {args.pcap}")
    else:
        os.environ.pop("PCAP_PATH", None)

    # ---------------- HTTP CLIENTS ----------------

    # ML backend (register / heartbeat / telemetry)
    http_ml = HTTPClient(
        server_url=config.server_url,
        token=config.token
    )

    # Dashboard backend (portal bind ONLY)
    http_dashboard = HTTPClient(
        server_url=config.dashboard_url,
        token=None
    )

    # ---------------- MQTT (OPTIONAL) ----------------

    mqtt = None
    if not args.no_mqtt:
        try:
            mqtt = MQTTClient(
                config.mqtt_broker,
                config.mqtt_port,
                token=config.token
            )
            mqtt.connect()
        except Exception as e:
            logger.error(
                f"MQTT client failed to start: {e}. Continuing without MQTT."
            )
            mqtt = None
    else:
        logger.info("MQTT disabled (HTTP-only mode)")

    # ---------------- START AGENT ----------------

    agent = NetworkAgent(
        config=config,
        comm_http=http_ml,
        dashboard_http=http_dashboard,
        comm_mqtt=mqtt
    )

    try:
        agent.run()
    except KeyboardInterrupt:
        logger.info("Agent stopped by user (KeyboardInterrupt)")
    except Exception as e:
        logger.exception(f"Unhandled exception in agent: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
