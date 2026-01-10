# dashboard/app/services/portal_approval.py
import time

class PortalApprovalStore:
    def __init__(self):
        self.approved_ips = {}  # ip -> timestamp

    def approve_ip(self, ip: str):
        self.approved_ips[ip] = time.time()

    def is_ip_approved(self, ip: str, ttl=300) -> bool:
        ts = self.approved_ips.get(ip)
        if not ts:
            return False
        return (time.time() - ts) < ttl

    def consume_ip(self, ip: str):
        self.approved_ips.pop(ip, None)


portal_approval_store = PortalApprovalStore()
