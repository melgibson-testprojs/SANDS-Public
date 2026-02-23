import json
try:
    import paho.mqtt.client as mqtt
    _HAS_PAHO = True
except Exception:
    _HAS_PAHO = False

from ..core.logger import get_logger
logger = get_logger("mqtt_client")


class MQTTClient:
    def __init__(self, broker: str, port: int, token: str = None, topic_prefix: str = "swarm"):
        self.broker = broker
        self.port = port
        self.token = token
        self.topic_prefix = topic_prefix.rstrip("/")
        self.client = None
        self._connected = False

        # 🔑 store callbacks per topic
        self._subscriptions = {}

        if _HAS_PAHO:
            self.client = mqtt.Client()
            if self.token:
                self.client.username_pw_set(username="token", password=self.token)

            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._dispatch_message

            # auto reconnect (IMPORTANT)
            self.client.reconnect_delay_set(min_delay=1, max_delay=30)
        else:
            logger.warning("paho-mqtt not installed; MQTTClient running as stub")

    # --------------------------
    # MQTT callbacks
    # --------------------------
    @staticmethod
    def _topic_matches(subscribed: str, actual: str) -> bool:
        sub_parts = subscribed.split("/")
        act_parts = actual.split("/")

        for i, sub in enumerate(sub_parts):
            if sub == "#":
                return True
            if i >= len(act_parts):
                return False
            if sub == "+":
                continue
            if sub != act_parts[i]:
                return False

        return len(sub_parts) == len(act_parts)
    
    def _on_connect(self, client, userdata, flags, rc):
        logger.info(f"mqtt connected rc={rc}")
        if rc == 0:
            self._connected = True

            # 🔁 resubscribe on reconnect
            for topic, (_, qos) in self._subscriptions.items():
                client.subscribe(topic, qos)
                logger.info(f"mqtt resubscribed: {topic}")
        else:
            logger.error(f"mqtt connect failed rc={rc}")

    def _on_disconnect(self, client, userdata, rc):
        logger.warning(f"mqtt disconnected rc={rc}")
        self._connected = False

    def _dispatch_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode().strip())
        except Exception:
            payload = {"raw": msg.payload.decode(errors="ignore")}

        for topic, (cb, _) in self._subscriptions.items():
            if self._topic_matches(topic, msg.topic):
                cb(payload)
                return



    # --------------------------
    # Public API
    # --------------------------

    def connect(self):
        if not _HAS_PAHO:
            logger.info("MQTT stub connect: no-op")
            return

        logger.info(f"Connecting MQTT → {self.broker}:{self.port}")
        self.client.connect(self.broker, self.port, keepalive=60)
        self.client.loop_start()

    def publish(self, topic: str, payload: dict, qos: int = 0, retain: bool = False):
        if not _HAS_PAHO:
            logger.info(f"[MQTT-STUB] {topic} -> {payload}")
            return

        full_topic = f"{self.topic_prefix}/{topic}"
        self.client.publish(
            full_topic,
            json.dumps(payload),
            qos=qos,
            retain=retain
        )

    def subscribe(self, topic: str, cb, qos: int = 0):
        if not _HAS_PAHO:
            logger.info(f"[MQTT-STUB] subscribed to {topic}")
            return

        full_topic = f"{self.topic_prefix}/{topic}"
        self._subscriptions[full_topic] = (cb, qos)

        if self._connected:
            self.client.subscribe(full_topic, qos)
            logger.info(f"mqtt subscribed: {full_topic}")
    
    

