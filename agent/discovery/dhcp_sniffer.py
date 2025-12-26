# agent/discovery/dhcp_sniffer.py

from scapy.all import sniff, DHCP, BOOTP
from agent.discovery.events import DeviceDiscoveredEvent
from agent.core.logger import get_logger

logger = get_logger("dhcp_sniffer")


class DHCPDeviceSniffer:
    def __init__(self, on_device_discovered):
        """
        on_device_discovered: callback(DeviceDiscoveredEvent)
        """
        self.callback = on_device_discovered

    def _handle_packet(self, pkt):
        if pkt.haslayer(DHCP) and pkt.haslayer(BOOTP):
            bootp = pkt[BOOTP]
            dhcp = pkt[DHCP]

            mac = bootp.chaddr[:6].hex(":")
            ip = bootp.yiaddr or "0.0.0.0"

            hostname = None
            for opt in dhcp.options:
                if isinstance(opt, tuple) and opt[0] == "hostname":
                    hostname = opt[1].decode(errors="ignore")

            logger.info(f"New DHCP device: {ip} {mac} {hostname}")

            event = DeviceDiscoveredEvent(
                ip=ip,
                mac=mac,
                hostname=hostname,
                source="dhcp"
            )
            self.callback(event)

    def run(self, iface=None):
        logger.info("Starting DHCP sniffer")
        sniff(
            filter="udp and (port 67 or 68)",
            prn=self._handle_packet,
            store=False,
            iface=iface
        )
