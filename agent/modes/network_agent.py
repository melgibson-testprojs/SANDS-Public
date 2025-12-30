import time
import random
import threading
import hashlib
from agent.core.logical_agents.registry import LogicalAgentRegistry
from agent.core.logical_agents.registry import DeviceState

from agent.core.logger import get_logger
from agent.modes.base_agent import BaseAgent
from agent.modes.agent_state import AgentState
from agent.utils.cic_feature_extractor import extract_cic_features

from agent.discovery.dhcp_sniffer import DHCPDeviceSniffer
from agent.discovery.arp_monitor import ARPMonitor
from agent.discovery.events import DeviceDiscoveredEvent

logger = get_logger("network_agent")

class NetworkAgent(BaseAgent):
    def __init__(self, config, comm_http, comm_mqtt=None):
        super().__init__(config, comm_http, comm_mqtt)
        self.polling_interval = config.polling_interval

        self.logical_registry = LogicalAgentRegistry(
            physical_agent_id=self.agent_id
        )

        self._warned_unknown_ips = set()
        self._warned_blocked_devices = set()

        self.auto_approve = True  # DEV ONLY

    def _pick_known_device_ip(self):
        """
        Pick a random known device IP from the logical registry.
        Returns None if no devices are known yet.
        """
        with self.logical_registry._lock:
            if not self.logical_registry.ip_index:
                return None
            return random.choice(list(self.logical_registry.ip_index.keys()))




    def _collect_flow(self):
        """Synthetic flow generator (D2 replaces this)."""
        now = time.time()
        packets = []

        src_ip = self._pick_known_device_ip()
        if not src_ip:
            return None

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

    def _on_device_discovered(self, event: DeviceDiscoveredEvent):
        device_id = self._generate_device_id(event.mac)

        created = self.logical_registry.register_device(
            device_id=device_id,
            ip=event.ip,
            mac=event.mac,
            hostname=event.hostname
        )

        if created:
            self.logger.info(
                "LOGICAL_AGENT_CREATED | "
                f"physical_agent={self.agent_id} | "
                f"device_id={device_id} | "
                f"ip={event.ip} | "
                f"mac={event.mac} | "
                f"hostname={event.hostname or 'UNKNOWN'} | "
                f"source={event.source} | "
                f"state=NEW"
            )
        else:
            self.logger.debug(
                f"KNOWN DEVICE | "
                f"device_id={device_id} | "
                f"IP={event.ip}"
            )
        
        # DEV ONLY — auto-approve devices
        if self.auto_approve:
            self.logical_registry.set_state(
                device_id,
                DeviceState.APPROVED
            )


    
    def _start_device_discovery(self):
        """
        Starts background sniffers for device discovery.
        Runs independently from packet capture.
        """

        self.logger.info("Starting device discovery subsystem")

        dhcp_sniffer = DHCPDeviceSniffer(self._on_device_discovered)
        arp_monitor = ARPMonitor(self._on_device_discovered)

        threading.Thread(
            target=dhcp_sniffer.run,
            daemon=True,
            name="DHCP-Sniffer"
        ).start()

        threading.Thread(
            target=arp_monitor.run,
            daemon=True,
            name="ARP-Monitor"
        ).start()

    def _generate_device_id(self, mac: str) -> str:
        """
        Stable logical agent ID:
        SHA256(physical_agent_id + MAC)
        """
        raw = f"{self.agent_id}:{mac}".encode()
        return hashlib.sha256(raw).hexdigest()[:16]


    def run(self):
        self.logger.info("NetworkAgent starting")

        # 🟢 STEP 1: start device discovery (background threads)
        self._start_device_discovery()

        # --- Registration loop (main thread) ---
        while self.state != AgentState.REGISTERED:
            self.logger.info("Waiting for backend registration...")
            self.register()
            time.sleep(2)

        self.logger.info("Agent successfully registered")

        # --- Main control loop ---
        while True:
            try:
                flow = self._collect_flow()
                if not flow:
                    continue

                device_id = self.logical_registry.resolve_device(flow["src_ip"])

                if not device_id:
                    if flow["src_ip"] not in self._warned_unknown_ips:
                        self.logger.warning(
                            f"FLOW FROM UNKNOWN DEVICE | src_ip={flow['src_ip']}"
                        )
                        self._warned_unknown_ips.add(flow["src_ip"])
                    continue
                
                state = self.logical_registry.get_state(device_id)

                if state != DeviceState.APPROVED:
                    if device_id not in self._warned_blocked_devices:
                        self.logger.info(
                            f"FLOW DROPPED | "
                            f"device_id={device_id} | "
                            f"state={state.value}"
                        )
                        self._warned_blocked_devices.add(device_id)
                    continue


                features = extract_cic_features(flow)

                payload = {
                    "agent_id": self.agent_id,
                    "logical_agent_id": device_id,
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
                self.logger.exception(f"Agent loop error: {e}")

            time.sleep(self.polling_interval)
