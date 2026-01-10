"""Main application entry point"""

import logging
import sys
import signal
import pyaudio
import numpy as np
from .config import DetectorConfig
from .mqtt_client import MQTTClient
from .ha_client import HAClient
from .audio_detector import AlarmDetector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


class DetectorApp:
    """Main application orchestrator"""

    def __init__(self):
        self.config = DetectorConfig()
        self.mqtt_client = None
        self.detector = None
        self.audio_stream = None
        self.p = None
        self.running = False

    def setup(self):
        """Initialize all components"""
        logger.info("=" * 60)
        logger.info("ACOUSTIC ALARM DETECTOR - PRODUCTION")
        logger.info("=" * 60)
        logger.info(f"Alarm Type: {self.config.alarm_type.upper()}")
        logger.info(f"Target Frequency: {self.config.target_frequency} Hz")
        logger.info(f"Sample Rate: {self.config.sample_rate} Hz")
        logger.info(f"Confirmation Cycles: {self.config.confirmation_cycles}")
        logger.info("=" * 60)

        # Initialize API Clients
        self.mqtt_client = MQTTClient(self.config)

        # Only pass token if it's actually set (not empty string)
        manual = (self.config.ha_token or "").strip()
        self.ha_client = HAClient(manual if manual else None)

        # Connect MQTT but don't exit if it fails (we have the API fallback)
        if not self.mqtt_client.connect():
            logger.warning("MQTT Connection failed. Will use Direct API fallback.")

        # Optional: Test HA API Connection (only log if it fails)
        if not self.ha_client.test_connection():
            logger.debug("HA API test failed, but will retry on actual alarm detection")

        # Initialize detector with hybrid callback
        def notification_callback(detected: bool):
            # Priority 1: MQTT (Official way for addons to create binary sensors)
            if self.mqtt_client.connected:
                self.mqtt_client.publish_alarm_state(detected)
                logger.info(
                    f"📡 MQTT: Alarm state published = {'ON' if detected else 'OFF'}"
                )
            else:
                # Priority 2: Direct API (Fallback when MQTT unavailable)
                logger.warning(
                    "MQTT not connected, using Supervisor API state update fallback"
                )
                self.ha_client.sync_notification(
                    detected, self.config.device_name, self.config.alarm_type
                )

        self.detector = AlarmDetector(self.config, mqtt_callback=notification_callback)

        # Initialize PyAudio safely
        try:
            logger.info("Initializing PyAudio...")
            self.p = pyaudio.PyAudio()
            self.list_audio_devices()
        except Exception as e:
            logger.error(f"CRITICAL: Failed to initialize PyAudio: {e}")
            logger.error(
                "This usually means audio drivers (ALSA) are missing or inaccessible."
            )
            sys.exit(1)

        try:
            device_index = self.config.audio_device_index

            # Basic validation to prevent Segfaults
            if device_index is not None:
                try:
                    dev_info = self.p.get_device_info_by_host_api_device_index(
                        0, device_index
                    )
                    logger.info(
                        f"Using manual audio device: {dev_info.get('name')} (Index {device_index})"
                    )
                    if dev_info.get("maxInputChannels") == 0:
                        logger.error(
                            f"Device index {device_index} has no input channels!"
                        )
                        self.list_audio_devices()
                        sys.exit(1)
                except Exception as e:
                    logger.error(f"Invalid device index {device_index}: {e}")
                    self.list_audio_devices()
                    sys.exit(1)
            else:
                logger.info("Using default audio device index (attempting auto-detect)")

            self.audio_stream = self.p.open(
                format=pyaudio.paInt16,
                channels=self.config.channels,
                rate=self.config.sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.config.chunk_size,
            )
            logger.info("Audio stream opened successfully")
        except Exception as e:
            logger.error(f"Failed to open audio stream: {e}")
            self.list_audio_devices()  # Show devices again on failure
            sys.exit(1)

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def list_audio_devices(self):
        """List all available audio input devices for user debugging"""
        logger.info("-" * 40)
        logger.info("AVAILABLE AUDIO DEVICES:")
        try:
            # Re-initialize if not exists
            if not self.p:
                self.p = pyaudio.PyAudio()

            info = self.p.get_host_api_info_by_index(0)
            num_devices = info.get("deviceCount")

            if num_devices == 0:
                logger.warning(
                    "No audio devices found! Check your 'privileged' and 'devices' settings."
                )

            for i in range(0, num_devices):
                device_info = self.p.get_device_info_by_host_api_device_index(0, i)
                if device_info.get("maxInputChannels") > 0:
                    logger.info(
                        f"Index {i}: {device_info.get('name')} (Input channels: {device_info.get('maxInputChannels')})"
                    )
        except Exception as e:
            logger.error(f"Could not list audio devices: {e}")
        logger.info("-" * 40)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}. Shutting down...")
        self.running = False

    def run(self):
        """Main processing loop"""
        self.running = True
        logger.info("Detector is running. Listening for alarm patterns...")

        try:
            while self.running:
                # Read audio chunk
                audio_data = self.audio_stream.read(
                    self.config.chunk_size, exception_on_overflow=False
                )
                audio_chunk = np.frombuffer(audio_data, dtype=np.int16)

                # Process audio
                self.detector.process_audio_chunk(audio_chunk)

        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up resources...")

        if self.audio_stream:
            try:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
            except Exception:
                pass

        if self.p:
            try:
                self.p.terminate()
            except Exception:
                pass

        if self.mqtt_client:
            self.mqtt_client.disconnect()

        logger.info("Shutdown complete")


def main():
    """Entry point"""
    app = DetectorApp()
    app.setup()
    app.run()


if __name__ == "__main__":
    main()
