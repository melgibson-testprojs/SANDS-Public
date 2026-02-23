import os
import math
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
from agent.comm.swarm_protocol import (
    SwarmTopics,
    SwarmMsgType,
    SwarmCode
)
from agent.traffic.scapy_flow_collector import ScapyFlowCollector
from risk.models import RiskEvent
from risk import config
from risk.rules import decide_action

from agent.comm.leader import LeaderElection
from agent.comm.consensus import VoteStore
from agent.comm.swarm_protocol import SwarmMsgType
import time


logger = get_logger("network_agent")

class NetworkAgent(BaseAgent):
    def __init__(self, config, comm_http, dashboard_http, comm_mqtt=None):
        super().__init__(config, comm_http, comm_mqtt)
        choice = input("Use Scapy live capture? (y/n): ").strip().lower()
        self.use_scapy = (choice == "y")

        self.dashboard_http = dashboard_http

        self.polling_interval = config.polling_interval

        self.logical_registry = LogicalAgentRegistry(
            physical_agent_id=self.agent_id
        )

        self.flow_collector = None

        if self.use_scapy:
            self.flow_collector = ScapyFlowCollector(
                iface=self.config.capture_iface
            )



        #self.portal_token = None

        self._warned_unknown_ips = set()
        self._warned_blocked_devices = set()
        self._portal_bind_sent = set()
        self._last_approval_sync = 0
        self._approval_poll_interval = 5.0  # seconds

        self.auto_approve = False  # DEV ONLY

        self.leader = LeaderElection(self.config.agent_id)
        self.vote_store = VoteStore()
        self.blocked_ips = set()
        self._vote_cooldown = {}   # target_id -> last_vote_timestamp
        self._vote_cooldown_secs = 15
        self.leader.register_agent(self.agent_id)
        self._last_swarm_status_log = 0
        self._swarm_status_interval = 30

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
        dst_port = random.choice([22, 23, 3389, 4444])
        #dst_port = 80

        src_bytes = 0
        dst_bytes = 0
        src_cnt = 200
        dst_cnt = 1

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

    def _get_next_flow(self):
        """
        Unified flow source:
        - Scapy (real traffic) OR
        - Synthetic generator
        """
        if self.use_scapy:
            return self.flow_collector.get_ready_flow()
        else:
            return self._collect_flow()


    def _on_device_discovered(self, event: DeviceDiscoveredEvent):
        #self._poll_portal_token()
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
            self._notify_dashboard_device_state(device_id)

            # if self.portal_token and event.mac not in self._portal_bind_sent:
            #     try:
            #         resp = self.dashboard_http.post(
            #             "/agent/bind",
            #             {
            #                 "portal_token": self.portal_token,
            #                 "mac": event.mac,
            #                 "agent_id": self.agent_id
            #             }
            #         )
            #         self._portal_bind_sent.add(event.mac)
            #         if resp.get("status") == "approved":
            #             self.portal_token = None
            #             self.logger.info("PORTAL TOKEN CONSUMED")
            #         self.logger.info(f"PORTAL_BIND_SENT | mac={event.mac}")
            #     except Exception as e:
            #         self.logger.warning(
            #             f"PORTAL_BIND_FAILED | mac={event.mac} | {e}"
            #         )


        else:
            self.logger.debug(
                f"KNOWN DEVICE | device_id={device_id} | IP={event.ip}"
            )


#    def _poll_portal_token(self):
#        if self.portal_token:
#            return
#        try:
#            resp = self.dashboard_http.get("/portal/pending")
#            token = resp.get("token")
#            if token:
#                self.portal_token = token
#                self.portal_ip = resp.get("ip")
#                self.logger.info("PORTAL TOKEN AUTO-RECEIVED")
#        except Exception:
#            pass

    def _poll_portal_tokens(self):
        try:
            resp = self.dashboard_http.get("/portal/pending_all")
            return resp.get("tokens", [])
        except Exception:
            return []

    def _notify_dashboard_device_state(self, device_id):
        device = self.logical_registry.get_device(device_id)
        if not device:
            return

        try:
            self.dashboard_http.post(
                "/api/devices/state",
                {
                    "device_id": device_id,
                    "agent_id": self.agent_id,
                    "state": device["state"].value,
                    "ip": device.get("ip"),
                    "mac": device.get("mac"),
                    "risk": device.get("risk", 0.0)
                }
            )
        except Exception:
            pass

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
        raw = f"{mac}".encode()
        return hashlib.sha256(raw).hexdigest()[:16]

    def _sync_approved_devices(self):
        """
        Poll dashboard for approved MACs and update local device states.
        """

        now = time.time()
        if now - self._last_approval_sync < self._approval_poll_interval:
            return

        self._last_approval_sync = now

        try:
            resp = self.dashboard_http.get("/api/approved_macs")
            approved_macs = set(m.lower() for m in resp.get("approved_macs", []))

            for device_id, device in self.logical_registry.devices.items():
                mac = device.get("mac", "").lower()
                current_state = device["state"]

                #MAC is approved in dashboard
                if mac and mac in approved_macs:
                    if current_state in (DeviceState.NEW, DeviceState.BLOCKED):

                        self.logger.info(
                            f"DEVICE_MANUAL_ALLOW | device_id={device_id}"
                        )

                        device["risk_engine"].reset()
                        device["risk"] = 0.0

                        self._vote_cooldown.pop(device_id, None)

                        self.logical_registry.set_state(
                            device_id,
                            DeviceState.APPROVED
                        )

                        self._notify_dashboard_device_state(device_id)

                else:
                    if current_state == DeviceState.APPROVED:
                        self.logical_registry.set_state(
                            device_id,
                            DeviceState.NEW
                        )
                        self._notify_dashboard_device_state(device_id)

        except Exception as e:
            self.logger.debug(f"Approval sync failed: {e}")

    def _try_bind_existing_devices(self):
        tokens = self._poll_portal_tokens()
        if not tokens:
            return

        for token in tokens:
            for device_id, device in self.logical_registry.devices.items():
                if device["state"] != DeviceState.NEW:
                    continue

                mac = device.get("mac")
                if not mac or mac in self._portal_bind_sent:
                    continue

                try:
                    resp = self.dashboard_http.post(
                        "/agent/bind",
                        {
                            "portal_token": token,
                            "mac": mac,
                            "agent_id": self.agent_id
                        }
                    )

                    if resp.get("status") == "approved":
                        self._portal_bind_sent.add(mac)
                        self.logger.info(
                            f"PORTAL_BIND_SUCCESS | token={token} | mac={mac}"
                        )
                        break  # one token → one device

                except Exception as e:
                    self.logger.warning(
                        f"PORTAL_BIND_FAILED | token={token} | mac={mac} | {e}"
                    )

    def _on_swarm_alert(self, msg: dict):
        lid = msg.get("lid")
        code = msg.get("c")
        score = float(msg.get("s", 0))

        if not lid:
            return

        device = self.logical_registry.get_device(lid)
        if not device:
            return

        # 🧠 Accumulate swarm risk
        risk_engine = device["risk_engine"]

        risk_engine.ingest(RiskEvent(
            source="swarm",
            code=code,
            score=score * config.SWARM_WARN_MULTIPLIER
        ))

        device["risk"] = risk_engine.state.value
        self._notify_dashboard_device_state(lid)

        triggered_by = msg.get("src", "unknown")

        self.logger.info(
            f"SWARM_ALERT | triggered_by={triggered_by} | "
            f"lid={lid} | code={code} | "
            f"risk={device['risk']:.2f}"
        )

        # # Local defensive reaction (TEMPORARY)
        # if device["risk"] > 3.0:
        #     self.logical_registry.set_state(
        #         lid,
        #         DeviceState.BLOCKED
        #     )
        #     self._notify_dashboard_device_state(lid)

    def _on_swarm_vote(self, msg: dict):
        msg_type = msg.get("t")
        src = msg.get("src")

        if src:
            self.leader.register_agent(src)

        if msg_type == "HELLO":
            self.leader.register_agent(msg.get("src"))
            self.logger.info(
                f"SWARM_MEMBER_DISCOVERED | agent={msg.get('src')}"
            )
            return

        elif msg_type == "VOTE_REQ":
            self._handle_vote_request(msg)

        elif msg_type == "VOTE_CAST":
            self._handle_vote_cast(msg)

        elif msg_type == "CONSENSUS":
            self._handle_consensus(msg)

    def _on_swarm_command(self, msg: dict):
        if msg.get("t") != SwarmMsgType.CMD:
            return

        code = msg.get("c")
        lid = msg.get("lid")

        self.logger.warning(
            f"SWARM_COMMAND | code={code} | lid={lid}"
        )

        if code == SwarmCode.QUARANTINE and lid:
            self.logical_registry.set_state(
                lid,
                DeviceState.BLOCKED
            )
            self._notify_dashboard_device_state(lid)
    
    def _handle_vote_request(self, msg: dict):
        target_id = msg.get("target_id")
        target_type = msg.get("target_type")

        if not target_id:
            return

        self.logger.info(
            f"VOTE_REQUEST_RECEIVED | "
            f"from={msg.get('src')} | "
            f"target={target_id} | "
            f"type={target_type}"
        )

        agree = False

        if target_type == "device":
            device = self.logical_registry.get_device(target_id)
            if device:
                if device["risk_engine"].should_block():
                    agree = True

        elif target_type == "ip":
            if target_id in self.blocked_ips:
                agree = True

        if agree:
            vote_msg = {
                "t": "VOTE_CAST",
                "target_id": target_id,
                "target_type": target_type,
                "voter": self.agent_id,
                "src": self.agent_id,
                "ts": time.time()
            }

            self.comm_mqtt.publish(
                SwarmTopics.GLOBAL_ALERTS,
                vote_msg
            )
    
    def _handle_vote_cast(self, msg: dict):
        if not self.leader.is_leader():
            return

        target_id = msg.get("target_id")
        voter = msg.get("voter")
        target_type = msg.get("target_type")

        if not target_id or not voter:
            return

        total_agents = len(self.leader.known_agents)
        quorum = math.ceil(total_agents * 0.6)

        current_votes = self.vote_store.get_vote_count(target_id)

        self.logger.info(
            f"VOTE_CAST_RECEIVED | voter={voter} | "
            f"target={target_id} | "
            f"votes={current_votes + 1}/{total_agents} | "
            f"quorum={quorum}"
        )

        reached = self.vote_store.add_vote(
            target_id,
            voter,
            total_agents=total_agents,
            target_type=target_type
        )

        if reached:
            self.logger.warning(
                f"CONSENSUS_REACHED | "
                f"leader={self.agent_id} | "
                f"target={target_id} | "
                f"votes>={quorum} | "
                f"decision=BLOCK"
            )

            consensus_msg = {
                "t": "CONSENSUS",
                "target_id": target_id,
                "target_type": target_type,
                "action": "BLOCK",
                "src": self.agent_id,
                "ts": time.time()
            }

            self.comm_mqtt.publish(
                SwarmTopics.GLOBAL_ALERTS,
                consensus_msg
            )

    def initiate_vote(self, target_type, target_id):
        if not self.comm_mqtt:
            return

        now = time.time()

        last_vote = self._vote_cooldown.get(target_id)

        if last_vote and (now - last_vote) < self._vote_cooldown_secs:
            remaining = int(self._vote_cooldown_secs - (now - last_vote))
            self.logger.warning(
                f"VOTE_CANCELLED | target={target_id} | "
                f"reason = Device on cooldown | retry_in={remaining}s"
            )
            return

        # Record vote time
        self._vote_cooldown[target_id] = now

        payload = {
            "t": "VOTE_REQ",
            "target_type": target_type,
            "target_id": target_id,
            "src": self.agent_id,
            "ts": now
        }

        self.comm_mqtt.publish(
            SwarmTopics.GLOBAL_ALERTS,
            payload
        )

        self.logger.info(
            f"VOTE_REQ_SENT | "
            f"initiator={self.agent_id} | "
            f"target={target_id} | "
            f"type={target_type}"
        )

    def _handle_consensus(self, msg: dict):
        if msg.get("action") != "BLOCK":
            return

        target_id = msg.get("target_id")
        target_type = msg.get("target_type")

        if target_type == "device":
            device = self.logical_registry.get_device(target_id)
            if device:
                self.logical_registry.set_state(
                    target_id,
                    DeviceState.BLOCKED
                )
                self._notify_dashboard_device_state(target_id)

        elif target_type == "ip":
            self.blocked_ips.add(target_id)

        self.logger.warning(
            f"CONSENSUS_APPLIED | "
            f"decided_by={msg.get('src')} | "
            f"target={target_id} | "
            f"type={target_type} | "
            f"action=BLOCK"
        )

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

        if self.use_scapy:
            self.flow_collector.start()
            self.logger.info("Scapy flow collector started")
        else:
            self.logger.info("Using synthetic flow generator")



        if self.comm_mqtt:
            # 🔥 CONNECT TO MQTT BROKER FIRST
            self.comm_mqtt.connect()

            # Listen to peer alerts
            self.comm_mqtt.subscribe(
                SwarmTopics.logical_alerts_all(),
                self._on_swarm_alert
            )

            # Listen to commands addressed to me
            self.comm_mqtt.subscribe(
                SwarmTopics.agent_commands(self.agent_id),
                self._on_swarm_command
            )

            self.comm_mqtt.subscribe(
                SwarmTopics.GLOBAL_ALERTS,
                self._on_swarm_vote
            )

            hello_msg = {
                "t": "HELLO",
                "src": self.agent_id,
                "ts": time.time()
            }

            self.comm_mqtt.publish(
                SwarmTopics.GLOBAL_ALERTS,
                hello_msg,
                qos=1,
                retain=True
            )
            
            self.logger.info(f"SWARM_HELLO_SENT | agent={self.agent_id}")

            self.logger.info("Swarm subscriptions active")


        # --- Main control loop ---
        while True:
            try:

                #self._poll_portal_token()

                self._try_bind_existing_devices()

                # 🔁 STEP A: sync approval state from dashboard
                self._sync_approved_devices()

                #this will print swarm status not imp
                now = time.time()

                if now - self._last_swarm_status_log >= self._swarm_status_interval:
                    total_agents = len(self.leader.known_agents)
                    leader_id = self.leader.compute_leader()
                    agents_list = sorted(self.leader.known_agents)

                    self.logger.info(
                        f"SWARM_STATUS | "
                        f"agents={total_agents} | "
                        f"leader={leader_id} | "
                        f"members={agents_list}"
                    )

                    self._last_swarm_status_log = now

                flow = self._get_next_flow()
                if not flow:
                    time.sleep(0.01)
                    continue
                
                if flow and flow["dst_ip"] in self.blocked_ips:
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
                device = self.logical_registry.get_device(device_id)
                
                if state == DeviceState.BLOCKED:
                    continue

                if state != DeviceState.APPROVED:
                    if device_id not in self._warned_blocked_devices:
                        self.logger.info(
                            f"FLOW DROPPED | "
                            f"device_id={device_id} | "
                            f"state={state.value}"
                        )
                        self._warned_blocked_devices.add(device_id)
                    continue

                self.logger.info(
                    f"FLOW ACCEPTED | device_id={device_id} | ip={flow['src_ip']}"
                )


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
                        "protocol": flow["protocol"],
                        "mac": device.get("mac")
                    }
                }



                if self.state == AgentState.REGISTERED:
                    resp = self.send_telemetry(payload)

                    #result = resp.get("prediction", {}) if resp else {}
                    
                    #To test Risk
                    result = {
                        "final_decision": "SUSPICIOUS",
                        "reconstruction_error": 999.0
                    }


                    # 🔑 normalize ML decision (THIS IS THE FIX)
                    decision = (
                        result.get("final_decision")
                        or result.get("decision")
                        or ""
                    )
                    decision = str(decision).upper()

                    risk_engine = device["risk_engine"]

                    if decision == "ATTACK":
                        risk_engine.ingest(RiskEvent(
                            source="ml",
                            code="ATTACK",
                            score=config.ML_ATTACK_SCORE
                        ))

                    elif decision == "SUSPICIOUS":
                        self.logger.warning(
                            f"ML_SUSPICIOUS_TRIGGERED | device={device_id}"
                        )


                        risk_engine.ingest(RiskEvent(
                            source="ml",
                            code="SUSPICIOUS",
                            score=config.ML_SUSPICIOUS_SCORE
                        ))

                    # Sync numeric risk
                    device["risk"] = risk_engine.state.value
                    self._notify_dashboard_device_state(device_id)


                    if result.get("final_decision") in ("SUSPICIOUS", "ATTACK"):
                        swarm_msg = {
                            "t": SwarmMsgType.WARN,
                            "c": SwarmCode.ANOM_BEHAV,
                            "s": float(result.get("reconstruction_error", 0)),
                            "src": self.agent_id,
                            "lid": device_id,
                            "ts": time.time()
                        }

                        if self.comm_mqtt:
                            self.comm_mqtt.publish(
                                SwarmTopics.logical_alerts(device_id),
                                swarm_msg,
                                qos=0
                            )

                self.heartbeat()

                # force decay even if no new events
                device["risk_engine"].tick()
                device["risk"] = device["risk_engine"].state.value

                last = device.get("_last_sent_risk")
                if last is None or abs(device["risk"] - last) >= 0.1:
                    self._notify_dashboard_device_state(device_id)
                    device["_last_sent_risk"] = device["risk"]


                new_state = decide_action(
                    device["risk_engine"],
                    device["state"]
                )

                if new_state == DeviceState.BLOCKED:
                    self.initiate_vote("device", device_id)

                elif new_state != device["state"]:
                    self.logical_registry.set_state(device_id, new_state)
                    self._notify_dashboard_device_state(device_id)


            except Exception as e:
                self.logger.exception(f"Agent loop error: {e}")

            time.sleep(self.polling_interval)
