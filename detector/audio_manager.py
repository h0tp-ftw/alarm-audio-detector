"""Robust audio device management with ALSA error handling"""
import pyaudio
import logging
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

class AudioDeviceManager:
    """Manages audio device enumeration and selection with error handling"""

    def __init__(self):
        self.p: Optional[pyaudio.PyAudio] = None

    def initialize(self) -> bool:
        """Initialize PyAudio with error handling"""
        try:
            self.p = pyaudio.PyAudio()
            logger.info("PyAudio initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize PyAudio: {e}")
            return False

    def list_input_devices(self) -> List[Dict]:
        """Enumerate all available input devices"""
        if not self.p:
            logger.error("PyAudio not initialized")
            return []

        devices = []
        default_input = self.p.get_default_input_device_info()

        for i in range(self.p.get_device_count()):
            try:
                info = self.p.get_device_info_by_index(i)

                # Only include input devices
                if info['maxInputChannels'] > 0:
                    is_default = (info['index'] == default_input['index'])
                    devices.append({
                        'index': info['index'],
                        'name': info['name'],
                        'sample_rate': int(info['defaultSampleRate']),
                        'channels': info['maxInputChannels'],
                        'is_default': is_default,
                        'host_api': self.p.get_host_api_info_by_index(info['hostApi'])['name']
                    })

            except Exception as e:
                logger.debug(f"Could not query device {i}: {e}")
                continue

        return devices

    def get_default_input_device(self) -> Optional[Dict]:
        """Get default input device info"""
        try:
            info = self.p.get_default_input_device_info()
            return {
                'index': info['index'],
                'name': info['name'],
                'sample_rate': int(info['defaultSampleRate']),
                'channels': info['maxInputChannels']
            }
        except Exception as e:
            logger.error(f"No default input device available: {e}")
            return None

    def test_device_format(self, device_index: int, sample_rate: int,
                          channels: int) -> bool:
        """Test if device supports specified format"""
        try:
            # Test if format is supported
            is_supported = self.p.is_format_supported(
                sample_rate,
                input_device=device_index,
                input_channels=channels,
                input_format=pyaudio.paInt16
            )
            return True
        except ValueError as e:
            logger.warning(f"Format not supported on device {device_index}: {e}")
            return False

    def open_stream(self, device_index: Optional[int], sample_rate: int,
                   channels: int, chunk_size: int, callback=None):
        """
        Open audio stream with robust error handling
        Reference: PyAudio documentation - proper stream initialization
        """
        if not self.p:
            raise RuntimeError("PyAudio not initialized")

        try:
            # Validate format first
            if device_index is not None:
                if not self.test_device_format(device_index, sample_rate, channels):
                    logger.warning(f"Device {device_index} may not support format")

            stream_params = {
                'format': pyaudio.paInt16,
                'channels': channels,
                'rate': sample_rate,
                'input': True,
                'frames_per_buffer': chunk_size,
            }

            if device_index is not None:
                stream_params['input_device_index'] = device_index

            if callback:
                stream_params['stream_callback'] = callback

            stream = self.p.open(**stream_params)

            logger.info(f"Audio stream opened: {sample_rate}Hz, {channels}ch, device={device_index}")
            return stream

        except Exception as e:
            logger.error(f"Failed to open audio stream: {e}")
            logger.info("Troubleshooting tips:")
            logger.info("  1. Check USB microphone connection")
            logger.info("  2. Verify ALSA configuration: arecord -L")
            logger.info("  3. Test recording: arecord -d 5 test.wav")
            raise

    def terminate(self):
        """Clean up PyAudio resources"""
        if self.p:
            self.p.terminate()
            logger.info("PyAudio terminated")
