#!/usr/bin/env python3
"""Local validation script for the three-part architecture.

Tests module imports, configuration loading, and component wiring
without requiring actual audio hardware or Home Assistant.

Usage: python3 test_architecture.py
"""

import sys
import os

# Add detector module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "detector"))


def test_imports():
    """Test that all modules can be imported."""
    print("=" * 50)
    print("TEST: Module Imports")
    print("=" * 50)

    try:
        from config import DetectorConfig, DetectorProfile, AudioSettings

        print("✅ config.py: DetectorConfig, DetectorProfile, AudioSettings")
    except Exception as e:
        print(f"❌ config.py: {e}")
        return False

    try:
        from listener import AudioListener, AudioConfig

        print("✅ listener.py: AudioListener, AudioConfig")
    except Exception as e:
        print(f"❌ listener.py: {e}")
        return False

    try:
        from detector import PatternDetector, BeepState

        print("✅ detector.py: PatternDetector, BeepState")
    except Exception as e:
        print(f"❌ detector.py: {e}")
        return False

    try:
        from sensor import SensorManager, SensorProfile

        print("✅ sensor.py: SensorManager, SensorProfile")
    except Exception as e:
        print(f"❌ sensor.py: {e}")
        return False

    return True


def test_config_loading():
    """Test configuration loading."""
    print("\n" + "=" * 50)
    print("TEST: Configuration Loading")
    print("=" * 50)

    from config import DetectorConfig

    try:
        config = DetectorConfig.from_environment()
        print(f"✅ Loaded config for device: {config.device_name}")
        print(
            f"   Audio: {config.audio.sample_rate}Hz, chunk={config.audio.chunk_size}"
        )
        print(f"   Profiles: {len(config.profiles)}")
        for p in config.profiles:
            print(f"     - {p.name}: {p.target_frequency}Hz, {p.beep_count} beeps")
        return True
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        return False


def test_component_wiring():
    """Test that components can be wired together."""
    print("\n" + "=" * 50)
    print("TEST: Component Wiring")
    print("=" * 50)

    import numpy as np
    from config import DetectorConfig, DetectorProfile
    from detector import PatternDetector

    try:
        # Create a test profile
        profile = DetectorProfile(
            name="test_smoke",
            device_class="smoke",
            target_frequency=3150.0,
            beep_count=3,
        )

        # Track callback invocations
        callback_count = [0]

        def mock_callback(detected: bool):
            callback_count[0] += 1
            print(f"   Callback received: detected={detected}")

        # Create detector with mock callback
        detector = PatternDetector(
            profile=profile,
            sample_rate=44100,
            chunk_size=4096,
            on_detection=mock_callback,
        )
        print("✅ PatternDetector created successfully")

        # Process a silent audio chunk
        silent_chunk = np.zeros(4096, dtype=np.int16)
        detector.process(silent_chunk)
        print("✅ Detector processed silent audio chunk")

        # Process a chunk with target frequency
        t = np.arange(4096) / 44100
        tone_chunk = (np.sin(2 * np.pi * 3150 * t) * 16000).astype(np.int16)
        detector.process(tone_chunk)
        print("✅ Detector processed tone audio chunk")

        return True
    except Exception as e:
        print(f"❌ Component wiring failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_sensor_manager():
    """Test sensor manager initialization (without HA connection)."""
    print("\n" + "=" * 50)
    print("TEST: Sensor Manager (no HA connection)")
    print("=" * 50)

    from sensor import SensorManager, SensorProfile

    try:
        profiles = [
            SensorProfile(name="smoke", device_class="smoke"),
            SensorProfile(name="co", device_class="gas"),
        ]

        manager = SensorManager(
            device_name="test_detector",
            profiles=profiles,
        )
        print("✅ SensorManager created with 2 profiles")

        # Test callback creation
        callback = manager.create_detection_callback("smoke")
        print("✅ Detection callback created for 'smoke' profile")

        return True
    except Exception as e:
        print(f"❌ SensorManager test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("\n🔧 ACOUSTIC ALARM DETECTOR - ARCHITECTURE VALIDATION\n")

    results = []

    results.append(("Module Imports", test_imports()))
    results.append(("Config Loading", test_config_loading()))
    results.append(("Component Wiring", test_component_wiring()))
    results.append(("Sensor Manager", test_sensor_manager()))

    print("\n" + "=" * 50)
    print("RESULTS SUMMARY")
    print("=" * 50)

    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {name}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("🎉 All tests passed! Architecture is valid.")
        return 0
    else:
        print("⚠️  Some tests failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
