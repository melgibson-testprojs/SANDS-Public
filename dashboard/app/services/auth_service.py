from enum import Enum
from typing import Optional
import re

class UserRole(str, Enum):
    ADMIN = "admin"
    VIEWER = "viewer"

class AuthService:
    def __init__(self):
        # Hardcoded for demonstration as per plan
        self.users = {
            "admin": {"password": "admin", "role": UserRole.ADMIN},
            "viewer": {"password": "viewer", "role": UserRole.VIEWER}
        }
        self.sessions = {} # token -> username
        self.opaque_to_real = {}
        self.real_to_opaque = {}

    def get_secure_id(self, real_id: str) -> str:
        if not real_id: return real_id
        if real_id in self.real_to_opaque:
            return self.real_to_opaque[real_id]
        
        import hashlib
        opaque = "dev_" + hashlib.md5(real_id.encode()).hexdigest()[:10]
        self.opaque_to_real[opaque] = real_id
        self.real_to_opaque[real_id] = opaque
        return opaque

    def resolve_id(self, secure_id: str) -> str:
        return self.opaque_to_real.get(secure_id, secure_id)

    def authenticate(self, username, password) -> Optional[UserRole]:
        user = self.users.get(username)
        if user and user["password"] == password:
            return user["role"]
        return None

    def mask_ip(self, ip: str) -> str:
        if not ip: return "-"
        segments = ip.split(".")
        if len(segments) == 4:
            return f"{segments[0]}.{segments[1]}.x.x"
        return "x.x.x.x"

    def mask_mac(self, mac: str) -> str:
        if not mac: return "-"
        prefix = ""
        if mac.startswith("mac:"):
            prefix = "mac:"
            mac = mac[4:]
            
        segments = mac.split(":")
        if len(segments) == 6:
            return f"{prefix}{segments[0]}:{segments[1]}:xx:xx:xx:xx"
        return f"{prefix}xx:xx:xx:xx:xx:xx"

    def apply_masking(self, data: any, role: UserRole):
        if role == UserRole.ADMIN:
            return data
        
        if isinstance(data, list):
            return [self.apply_masking(item, role) for item in data]
        
        if isinstance(data, dict):
            new_data = data.copy()
            if "ip" in new_data:
                new_data["ip"] = self.mask_ip(new_data["ip"])
            if "mac" in new_data:
                new_data["mac"] = self.mask_mac(new_data["mac"])
            
            # Use Opaque ID for keys to preserve route functionality
            if "key" in new_data:
                new_data["key"] = self.get_secure_id(new_data["key"])
            if "device" in new_data:
                new_data["device"] = self.get_secure_id(new_data["device"])
            
            # Masking in nested descriptions (for logs)
            if "description" in new_data:
                desc = new_data["description"]
                # Mask IP-like patterns
                desc = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "xxx.xxx.xxx.xxx", desc)
                # Mask MAC-like patterns
                desc = re.sub(r"\b([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\b", "xx:xx:xx:xx:xx:xx", desc)
                new_data["description"] = desc
                
            return new_data
        
        return data

auth_service = AuthService()
