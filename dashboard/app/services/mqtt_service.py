import paho.mqtt.client as mqtt
import json
import os
import time

class MQTTService:
    def __init__(self):
        self.broker = os.environ.get("MQTT_BROKER", "localhost")
        self.port = int(os.environ.get("MQTT_PORT", 1883))
        self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        self.connected = False

    def connect(self):
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            self.connected = True
            print(f"Connected to MQTT broker at {self.broker}:{self.port}")
        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}")

    def publish(self, topic, payload):
        if not self.connected:
            self.connect()
        
        if self.connected:
            self.client.publish(topic, json.dumps(payload))
            return True
        return False

    def trigger_swarm_alert(self, device_id, code, score, src="debug_page"):
        topic = f"swarm/logical/{device_id}/alerts"
        payload = {
            "t": "WARN",
            "c": code,
            "s": score,
            "src": src,
            "lid": device_id,
            "ts": time.time()
        }
        return self.publish(topic, payload)

    def trigger_vote_request(self, target_id, target_type="device", src="debug_page"):
        topic = "swarm/global/alerts"
        payload = {
            "t": "VOTE_REQ",
            "target_id": target_id,
            "target_type": target_type,
            "src": src,
            "ts": time.time()
        }
        return self.publish(topic, payload)

    def trigger_consensus(self, target_id, target_type="device", action="BLOCK", src="debug_page"):
        topic = "swarm/global/alerts"
        payload = {
            "t": "CONSENSUS",
            "target_id": target_id,
            "target_type": target_type,
            "action": action,
            "src": src,
            "ts": time.time()
        }
        return self.publish(topic, payload)

mqtt_service = MQTTService()
