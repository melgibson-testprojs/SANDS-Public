import time
import os
import random
from .base_agent import BaseAgent
from ..core.logger import get_logger
from ..utils.cic_feature_extractor import extract_cic_features, FEATURE_NAMES

logger = get_logger("network_agent")

def _make_synthetic_packet(ts, src_ip, dst_ip, src_port, dst_port, proto="TCP", length=100, flags="PA"):
    return {
        "ts": ts,
        "src_ip": src_ip,
        "dst_ip": dst_ip,
        "src_port": src_port,
        "dst_port": dst_port,
        "proto": proto,
        "length": length,
        "flags": flags,
    }

class NetworkAgent(BaseAgent):
    def __init__(self, config, comm_http, comm_mqtt=None):
        super().__init__(config, comm_http, comm_mqtt)
        self.polling_interval = config.polling_interval
        # Optionally set PCAP_PATH env var later to point to real capture
        self.pcap_path = os.environ.get("PCAP_PATH", None)

    def _collect_flow(self):
        """
        CURRENT (default): produce a synthetic aggregated flow (packets list + directional bytes/counts)
        Future: if PCAP_PATH is set and scapy available, parse pcap and aggregate into flows here.
        """
        # simple synthetic flow: 8-12 packets over short duration
        now = time.time()
        num_pkts = random.randint(6, 12)
        src_ip = "10.0.0.5"
        dst_ip = "192.0.2.10"
        src_port = random.randint(1024, 65535)
        dst_port = 80
        proto = "TCP"
        ts_list = [now + i * (random.random() * 0.02 + 0.001) for i in range(num_pkts)]
        packets = []
        src_to_dst_bytes = 0
        dst_to_src_bytes = 0
        src_to_dst_cnt = 0
        dst_to_src_cnt = 0

        # create bursts where forward packets are more frequent
        for i, ts in enumerate(ts_list):
            # alternate directions somewhat
            if i % 3 != 0:
                # forward
                length = random.randint(40, 1500)
                pkt = _make_synthetic_packet(ts, src_ip, dst_ip, src_port, dst_port, proto, length, flags=random.choice(["PA","A","P","PA"]))
                packets.append(pkt)
                src_to_dst_bytes += length
                src_to_dst_cnt += 1
            else:
                # backward
                length = random.randint(40, 1200)
                pkt = _make_synthetic_packet(ts, dst_ip, src_ip, dst_port, src_port, proto, length, flags=random.choice(["A","PA",""]))
                packets.append(pkt)
                dst_to_src_bytes += length
                dst_to_src_cnt += 1

        pkt_counts = {"total": len(packets), "src_to_dst": src_to_dst_cnt, "dst_to_src": dst_to_src_cnt}
        directional_bytes = {"src_to_dst": src_to_dst_bytes, "dst_to_src": dst_to_src_bytes}
        flow = {
            "src_ip": src_ip,
            "dst_ip": dst_ip,
            "src_port": src_port,
            "dst_port": dst_port,
            "protocol": proto,
            "start_ts": min(p.get("ts", time.time()) for p in packets),
            "end_ts": max(p.get("ts", time.time()) for p in packets),
            "packets": packets,
            "total_bytes": src_to_dst_bytes + dst_to_src_bytes,
            "directional_bytes": directional_bytes,
            "pkt_counts": pkt_counts,
            "tcp_flag_counts": {},  # optional; extractor is defensive
        }
        return flow

    def run(self):
        logger.info("NetworkAgent is starting its main loop...")
        self.register()

        while True:
            try:
                flow = self._collect_flow()
                # compute 77-dim features
                features = extract_cic_features(flow)
                # include feature names optionally for debugging
                if os.environ.get("DEBUG_FEATURE_NAMES", "0") == "1":
                    # attach names for human readability (not for server model)
                    payload = {
                        "agent_id": self.agent_id,
                        "ts": time.time(),
                        "features": features,
                        "feature_names": FEATURE_NAMES,
                        "flow_meta": {
                            "src_ip": flow.get("src_ip"),
                            "dst_ip": flow.get("dst_ip"),
                            "src_port": flow.get("src_port"),
                            "dst_port": flow.get("dst_port"),
                            "protocol": flow.get("protocol"),
                        }
                    }
                else:
                    payload = {
                        "agent_id": self.agent_id,
                        "ts": time.time(),
                        "features": features,
                        "flow_meta": {
                            "src_ip": flow.get("src_ip"),
                            "dst_ip": flow.get("dst_ip"),
                            "src_port": flow.get("src_port"),
                            "dst_port": flow.get("dst_port"),
                            "protocol": flow.get("protocol"),
                        }
                    }

                self.send_telemetry(payload)

            except Exception as e:
                logger.error(f"main loop error: {e}")

            # heartbeat on interval boundary as well
            self.heartbeat()
            time.sleep(self.polling_interval)
