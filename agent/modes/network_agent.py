import time
import random

from agent.core.logger import get_logger
from agent.modes.base_agent import BaseAgent
from agent.modes.agent_state import AgentState
from agent.utils.cic_feature_extractor import extract_cic_features

logger = get_logger("network_agent")


class NetworkAgent(BaseAgent):
    def __init__(self, config, comm_http, comm_mqtt=None):
        super().__init__(config, comm_http, comm_mqtt)
        self.polling_interval = config.polling_interval

    def _collect_flow(self):
        """Synthetic flow generator (D2 replaces this)."""
        now = time.time()
        packets = []

        src_ip = "10.0.0.5"
        dst_ip = "192.0.2.10"
        src_port = random.randint(1024, 65535)
        dst_port = 80

        src_bytes = 0
        dst_bytes = 0
        src_cnt = 0
        dst_cnt = 0

        for i in range(8):
            ts = now + i * 0.01
            length = random.randint(100, 1500)

            if i % 3 == 0:
                packets.append({
                    "ts": ts,
                    "src_ip": dst_ip,
                    "dst_ip": src_ip,
                    "src_port": dst_port,
                    "dst_port": src_port,
                    "length": length,
                    "flags": "A"
                })
                dst_bytes += length
                dst_cnt += 1
            else:
                packets.append({
                    "ts": ts,
                    "src_ip": src_ip,
                    "dst_ip": dst_ip,
                    "src_port": src_port,
                    "dst_port": dst_port,
                    "length": length,
                    "flags": "PA"
                })
                src_bytes += length
                src_cnt += 1

        return {
            "src_ip": src_ip,
            "dst_ip": dst_ip,
            "src_port": src_port,
            "dst_port": dst_port,
            "protocol": "TCP",
            "start_ts": packets[0]["ts"],
            "end_ts": packets[-1]["ts"],
            "packets": packets,
            "pkt_counts": {
                "total": len(packets),
                "src_to_dst": src_cnt,
                "dst_to_src": dst_cnt
            },
            "directional_bytes": {
                "src_to_dst": src_bytes,
                "dst_to_src": dst_bytes
            }
        }

    def run(self):
        logger.info("NetworkAgent starting")

        # --- Registration loop ---
        while self.state != AgentState.REGISTERED:
            logger.info("Waiting for backend registration...")
            self.register()

        # --- Main loop ---
        while True:
            try:
                flow = self._collect_flow()
                features = extract_cic_features(flow)

                payload = {
                    "agent_id": self.agent_id,
                    "ts": time.time(),
                    "features": features,
                    "flow_meta": {
                        "src_ip": flow["src_ip"],
                        "dst_ip": flow["dst_ip"],
                        "src_port": flow["src_port"],
                        "dst_port": flow["dst_port"],
                        "protocol": flow["protocol"]
                    }
                }

                if self.state == AgentState.REGISTERED:
                    self.send_telemetry(payload)

                self.heartbeat()

            except Exception as e:
                logger.exception(f"Agent loop error: {e}")

            time.sleep(self.polling_interval)