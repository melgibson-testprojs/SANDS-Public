from scapy.all import sniff, IP, TCP, UDP
import time
import threading

FLOW_TIMEOUT = 5.0  # reduced from 10.0
MAX_FLOW_DURATION = 30.0  # reduced from 60.0

class ScapyFlowCollector:
    def __init__(self, iface=None):
        self.iface = iface
        self.flows = {}
        self.ready_flows = []
        self.lock = threading.Lock()

    def start(self):
        t = threading.Thread(
            target=self._sniff,
            daemon=True,
            name="Scapy-Sniffer"
        )
        t.start()

    def _sniff(self):
        sniff(
            iface=self.iface,
            prn=self._on_packet,
            store=False
        )

    def _flow_key(self, pkt):
        if IP not in pkt:
            return None

        ip = pkt[IP]

        if TCP in pkt:
            l4 = pkt[TCP]
            proto = "TCP"
        elif UDP in pkt:
            l4 = pkt[UDP]
            proto = "UDP"
        else:
            return None

        return (ip.src, ip.dst, l4.sport, l4.dport, proto)


    def _on_packet(self, pkt):
        forward_key = self._flow_key(pkt)
        if not forward_key:
            return

        reverse_key = (forward_key[1], forward_key[0], forward_key[3], forward_key[2], forward_key[4])
        now = time.time()

        with self.lock:
            if forward_key in self.flows:
                key = forward_key
                direction = "src_to_dst"
            elif reverse_key in self.flows:
                key = reverse_key
                direction = "dst_to_src"
            else:
                key = forward_key
                direction = "src_to_dst"
                self.flows[key] = {
                    "src_ip": key[0],
                    "dst_ip": key[1],
                    "src_port": key[2],
                    "dst_port": key[3],
                    "protocol": key[4],
                    "start_ts": now,
                    "end_ts": now,
                    "packets": [],
                    "pkt_counts": {
                        "total": 0,
                        "src_to_dst": 0,
                        "dst_to_src": 0
                    },
                    "directional_bytes": {
                        "src_to_dst": 0,
                        "dst_to_src": 0
                    },
                    "last_seen": now
                }

            flow = self.flows[key]
            flow["end_ts"] = now
            flow["last_seen"] = now

            length = len(pkt)
            flags = pkt[TCP].flags.flagrepr() if TCP in pkt else ""

            flow["packets"].append({
                "ts": now,
                "src_ip": pkt[IP].src,
                "dst_ip": pkt[IP].dst,
                "src_port": pkt.sport,
                "dst_port": pkt.dport,
                "length": length,
                "flags": flags
            })

            flow["pkt_counts"]["total"] += 1
            flow["pkt_counts"][direction] += 1
            flow["directional_bytes"][direction] += length

    def flush_expired(self):
        now = time.time()
        expired = []

        with self.lock:
            for key, flow in self.flows.items():
                flow_age = now - flow["start_ts"]
                idle = now - flow["last_seen"]

                if idle > FLOW_TIMEOUT or flow_age > MAX_FLOW_DURATION:
                    expired.append(key)
            
            for key in expired:
                flow_data = self.flows.pop(key)
                self.ready_flows.append(flow_data)
                print(
                    f"[ScapyFlowCollector] FINALIZE FLOW "
                    f"{flow_data['src_ip']}:{flow_data['src_port']} → "
                    f"{flow_data['dst_ip']}:{flow_data['dst_port']} | "
                    f"pkts={len(flow_data['packets'])}"
                )


    def get_ready_flow(self):
        self.flush_expired()

        with self.lock:
            if not self.ready_flows:
                return None

            flow = self.ready_flows.pop(0)

        # 🔍 minimum packet sanity
        if len(flow["packets"]) < 1:
            return None

        return flow
