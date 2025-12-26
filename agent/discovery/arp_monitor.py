# agent/discovery/arp_monitor.py

from scapy.all import sniff, ARP
from agent.discovery.events import DeviceDiscoveredEvent
from agent.core.logger import get_logger

logger = get_logger("arp_monitor")


class ARPMonitor:
    def __init__(self, on_device_discovered):
        self.callback = on_device_discovered
        self.seen = set()

    def _handle_packet(self, pkt):
        if pkt.haslayer(ARP) and pkt[ARP].op in (1, 2):
            ip = pkt[ARP].psrc
            mac = pkt[ARP].hwsrc

            key = (ip, mac)
            if key in self.seen:
                return

            self.seen.add(key)

            logger.info(f"ARP discovered device: {ip} {mac}")

            event = DeviceDiscoveredEvent(
                ip=ip,
                mac=mac,
                source="arp"
            )
            self.callback(event)

    def run(self, iface=None):
        logger.info("Starting ARP monitor")
        sniff(
            filter="arp",
            prn=self._handle_packet,
            store=False,
            iface=iface
        )
