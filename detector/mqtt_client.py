"""MQTT client with Home Assistant auto-discovery support"""

import json
import logging
import paho.mqtt.client as mqtt
from typing import Optional
from .config import DetectorConfig

logger = logging.getLogger(__name__)


class MQTTClient:
    """MQTT client for Home Assistant integration"""

    def __init__(self, config: DetectorConfig):
        self.config = config
        self.client: Optional[mqtt.Client] = None
        self.connected = False

    def connect(self) -> bool:
        """Connect to MQTT broker and publish discovery config"""
        try:
            self.client = mqtt.Client(client_id=f"{self.config.device_name}_detector")

            # Set up callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect

            # Set authentication if provided
            if self.config.mqtt_user:
                self.client.username_pw_set(
                    self.config.mqtt_user, self.config.mqtt_password
                )

            # Set Last Will and Testament for availability
            self.client.will_set(
                self.config.mqtt_availability_topic,
                payload="offline",
                qos=1,
                retain=True,
            )

            # Connect to broker
            logger.info(
                f"Connecting to MQTT broker at {self.config.mqtt_host}:{self.config.mqtt_port}"
            )
            self.client.connect(
                self.config.mqtt_host, self.config.mqtt_port, keepalive=60
            )

            # Start network loop in background
            self.client.loop_start()

            return True

        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            return False

    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        if rc == 0:
            logger.info("Connected to MQTT broker successfully")
            self.connected = True

            # Publish availability
            self.publish_availability("online")

            # Publish discovery configuration for automatic HA integration
            self._publish_discovery_config()

            # Publish initial state to avoid 'Unknown' in Home Assistant
            self.publish_alarm_state(False)
        else:
            logger.error(f"Failed to connect to MQTT broker. Return code: {rc}")
            self.connected = False

    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker"""
        logger.warning(f"Disconnected from MQTT broker. Return code: {rc}")
        self.connected = False

    def _publish_discovery_config(self):
        """
        Publish MQTT Discovery config for automatic Home Assistant registration
        Reference: https://www.home-assistant.io/integrations/mqtt/#discovery
        """
        alarm_type_label = "Smoke" if self.config.alarm_type == "smoke" else "CO"

        discovery_payload = {
            "name": f"{alarm_type_label} Alarm Detector",
            "unique_id": f"{self.config.device_name}_alarm",
            "device_class": "smoke" if self.config.alarm_type == "smoke" else "gas",
            "state_topic": self.config.mqtt_state_topic,
            "availability_topic": self.config.mqtt_availability_topic,
            "payload_on": "ON",
            "payload_off": "OFF",
            "payload_available": "online",
            "payload_not_available": "offline",
            "qos": 1,
            "device": {
                "identifiers": [self.config.device_name],
                "name": f"Acoustic {alarm_type_label} Alarm Detector",
                "model": "Acoustic DSP Detector v8",
                "manufacturer": "Open Source Community",
                "sw_version": "8.4.1",
            },
        }

        logger.info(
            f"Publishing MQTT Discovery config to {self.config.mqtt_discovery_topic}"
        )
        self.client.publish(
            self.config.mqtt_discovery_topic,
            payload=json.dumps(discovery_payload),
            qos=1,
            retain=True,
        )
        logger.info(
            "MQTT Discovery config published - device should appear in Home Assistant"
        )

    def publish_alarm_state(self, detected: bool):
        """Publish alarm detection state"""
        if not self.connected:
            logger.warning("Cannot publish - not connected to MQTT broker")
            return

        payload = "ON" if detected else "OFF"
        logger.info(f"Publishing alarm state: {payload}")

        self.client.publish(
            self.config.mqtt_state_topic, payload=payload, qos=1, retain=False
        )

    def publish_availability(self, status: str):
        """Publish availability status"""
        if self.client:
            self.client.publish(
                self.config.mqtt_availability_topic, payload=status, qos=1, retain=True
            )

    def disconnect(self):
        """Disconnect from MQTT broker"""
        if self.client:
            self.publish_availability("offline")
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("Disconnected from MQTT broker")
