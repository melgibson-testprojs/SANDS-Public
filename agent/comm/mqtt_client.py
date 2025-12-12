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
        self.topic_prefix = topic_prefix.rstrip('/')
        self.client = None
        self._connected = False

        if _HAS_PAHO:
            self.client = mqtt.Client()
            if self.token:
                self.client.username_pw_set(username="token", password=self.token)
            # TLS can be added later for production
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
        else:
            logger.warning("paho-mqtt not installed; MQTTClient running as stub")

    def _on_connect(self, client, userdata, flags, rc):
        logger.info(f"mqtt connected rc={rc}")
        self._connected = True

    def _on_disconnect(self, client, userdata, rc):
        logger.info(f"mqtt disconnected rc={rc}")
        self._connected = False

    def connect(self):
        if not _HAS_PAHO:
            logger.info("MQTT stub connect: no-op")
            return
        self.client.connect(self.broker, self.port)
        self.client.loop_start()

    def publish(self, topic: str, payload: dict):
        full_topic = f"{self.topic_prefix}/{topic}"
        if not _HAS_PAHO:
            logger.info(f"MQTT stub publish to {full_topic}: {payload}")
            return
        self.client.publish(full_topic, payload=str(payload))

    def subscribe(self, topic: str, cb):
        if not _HAS_PAHO:
            logger.info("MQTT stub subscribe: no-op")
            return

        def _on_message(client, userdata, msg):
            try:
                import json
                payload = json.loads(msg.payload)
            except Exception:
                payload = msg.payload.decode(errors='ignore')
            cb(payload)

        full_topic = f"{self.topic_prefix}/{topic}"
        self.client.subscribe(full_topic)
        self.client.on_message = _on_message
