"""Audio listener component for capturing audio input.

This module handles:
- PyAudio initialization and device management
- Audio stream capture and buffering
- Callback-based chunk delivery to detectors
"""

import logging
import pyaudio
import numpy as np
from typing import Callable, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AudioConfig:
    """Audio capture configuration."""

    sample_rate: int = 44100
    chunk_size: int = 4096
    channels: int = 1
    device_index: Optional[int] = None


class AudioListener:
    """Handles audio capture from microphone input."""

    def __init__(
        self, config: AudioConfig, on_audio_chunk: Callable[[np.ndarray], None]
    ):
        """Initialize the audio listener.

        Args:
            config: Audio configuration settings
            on_audio_chunk: Callback function to receive audio chunks
        """
        self.config = config
        self.on_audio_chunk = on_audio_chunk
        self._pyaudio: Optional[pyaudio.PyAudio] = None
        self._stream: Optional[pyaudio.Stream] = None
        self._running = False

    def setup(self) -> bool:
        """Initialize PyAudio and open the audio stream.

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Initializing PyAudio...")
            self._pyaudio = pyaudio.PyAudio()
            self._list_devices()

            # Validate device index if specified
            if self.config.device_index is not None:
                if not self._validate_device(self.config.device_index):
                    return False
                logger.info(f"Using audio device index: {self.config.device_index}")
            else:
                logger.info("Using default audio device")

            # Open audio stream
            self._stream = self._pyaudio.open(
                format=pyaudio.paInt16,
                channels=self.config.channels,
                rate=self.config.sample_rate,
                input=True,
                input_device_index=self.config.device_index,
                frames_per_buffer=self.config.chunk_size,
            )
            logger.info("✅ Audio stream opened successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize audio: {e}")
            self._list_devices()
            return False

    def _validate_device(self, device_index: int) -> bool:
        """Validate that a device index is usable for input."""
        try:
            dev_info = self._pyaudio.get_device_info_by_host_api_device_index(
                0, device_index
            )
            if dev_info.get("maxInputChannels", 0) == 0:
                logger.error(f"Device index {device_index} has no input channels!")
                return False
            logger.info(
                f"Device: {dev_info.get('name')} (Inputs: {dev_info.get('maxInputChannels')})"
            )
            return True
        except Exception as e:
            logger.error(f"Invalid device index {device_index}: {e}")
            return False

    def _list_devices(self) -> None:
        """List all available audio input devices."""
        logger.info("-" * 40)
        logger.info("AVAILABLE AUDIO DEVICES:")
        try:
            if not self._pyaudio:
                return

            info = self._pyaudio.get_host_api_info_by_index(0)
            num_devices = info.get("deviceCount", 0)

            if num_devices == 0:
                logger.warning("No audio devices found!")
                return

            for i in range(num_devices):
                device_info = self._pyaudio.get_device_info_by_host_api_device_index(
                    0, i
                )
                if device_info.get("maxInputChannels", 0) > 0:
                    logger.info(
                        f"  Index {i}: {device_info.get('name')} "
                        f"(Inputs: {device_info.get('maxInputChannels')})"
                    )
        except Exception as e:
            logger.error(f"Could not list devices: {e}")
        logger.info("-" * 40)

    def start(self) -> None:
        """Start the audio capture loop."""
        if not self._stream:
            logger.error("Audio stream not initialized. Call setup() first.")
            return

        self._running = True
        logger.info("🎤 Listener started - capturing audio...")

        try:
            while self._running:
                # Read audio chunk
                audio_data = self._stream.read(
                    self.config.chunk_size, exception_on_overflow=False
                )
                audio_chunk = np.frombuffer(audio_data, dtype=np.int16)

                # Deliver to callback
                self.on_audio_chunk(audio_chunk)

        except Exception as e:
            if self._running:  # Only log if not intentionally stopped
                logger.error(f"Error in audio capture loop: {e}", exc_info=True)

    def stop(self) -> None:
        """Stop the audio capture loop."""
        self._running = False
        logger.info("🛑 Listener stopping...")

    def cleanup(self) -> None:
        """Release audio resources."""
        logger.info("Cleaning up audio resources...")

        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        if self._pyaudio:
            try:
                self._pyaudio.terminate()
            except Exception:
                pass
            self._pyaudio = None

        logger.info("Audio cleanup complete")
