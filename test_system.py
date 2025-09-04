#!/usr/bin/env python3
"""
System test script for Raspberry Pi DMX Light Show
Tests audio input, DMX output, and light effects without full application.
"""

import time
import sys
import yaml
import logging
from pathlib import Path

# Import our modules
try:
    from audio_processor import AudioProcessor
    from dmx_controller import DMXController
    from light_effects import LightEffectsEngine
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)

def setup_logging():
    """Setup basic logging for testing."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def load_config():
    """Load configuration file."""
    config_file = 'config.yaml'
    if not Path(config_file).exists():
        print(f"Error: Configuration file '{config_file}' not found!")
        return None
    
    try:
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return None

def test_audio_input(config):
    """Test audio input and processing."""
    print("\n🎵 Testing Audio Input...")
    print("-" * 40)
    
    try:
        audio_processor = AudioProcessor(config)
        print("✅ Audio processor initialized")
        
        # Start audio processing
        audio_processor.start()
        print("✅ Audio processing started")
        
        # Test for a few seconds
        print("📊 Monitoring audio for 10 seconds...")
        for i in range(10):
            time.sleep(1)
            features = audio_processor.get_audio_features()
            
            volume = features['smoothed_volume']
            beat = "🔴" if features['beat_detected'] else "⚫"
            tempo = features['tempo']
            
            print(f"   Volume: {volume:.3f} | Beat: {beat} | Tempo: {tempo:.0f} BPM")
        
        audio_processor.stop()
        print("✅ Audio test completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Audio test failed: {e}")
        return False

def test_dmx_output(config):
    """Test DMX output and light control."""
    print("\n💡 Testing DMX Output...")
    print("-" * 40)
    
    try:
        dmx_controller = DMXController(config)
        print("✅ DMX controller initialized")
        
        dmx_controller.start()
        print("✅ DMX output started")
        
        # Test light patterns
        print("🌈 Testing color patterns...")
        
        # Red
        print("   Testing RED...")
        dmx_controller.set_all_lights_rgb(255, 0, 0, 200)
        time.sleep(2)
        
        # Green
        print("   Testing GREEN...")
        dmx_controller.set_all_lights_rgb(0, 255, 0, 200)
        time.sleep(2)
        
        # Blue
        print("   Testing BLUE...")
        dmx_controller.set_all_lights_rgb(0, 0, 255, 200)
        time.sleep(2)
        
        # White
        print("   Testing WHITE...")
        dmx_controller.set_all_lights_rgb(255, 255, 255, 200)
        time.sleep(2)
        
        # Fade to black
        print("   Fading to black...")
        dmx_controller.blackout()
        time.sleep(1)
        
        dmx_controller.stop()
        print("✅ DMX test completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ DMX test failed: {e}")
        return False

def test_effects_engine(config):
    """Test light effects engine."""
    print("\n✨ Testing Effects Engine...")
    print("-" * 40)
    
    try:
        # Create DMX controller
        dmx_controller = DMXController(config)
        dmx_controller.start()
        
        # Create effects engine
        effects_engine = LightEffectsEngine(config, dmx_controller)
        print("✅ Effects engine initialized")
        
        # Test different modes
        modes = ['pulse', 'chase', 'fade', 'auto']
        
        for mode in modes:
            print(f"   Testing {mode} mode...")
            effects_engine.set_mode(mode)
            
            # Simulate audio features
            for i in range(20):  # 2 seconds at 10 FPS
                # Simulate beat every 0.5 seconds
                beat_detected = (i % 5) == 0
                
                fake_features = {
                    'volume': 0.5 + 0.3 * (i % 10) / 10,
                    'smoothed_volume': 0.6,
                    'beat_detected': beat_detected,
                    'beat_strength': 1.0 if beat_detected else 0.0,
                    'tempo': 120,
                    'frequency_powers': {
                        'bass': 0.7 if beat_detected else 0.3,
                        'mid': 0.5,
                        'treble': 0.4
                    },
                    'time_since_beat': 0.1 if beat_detected else 0.5
                }
                
                effects_engine.update(fake_features)
                time.sleep(0.1)
        
        # Test palettes
        print("   Testing color palettes...")
        palettes = ['energetic', 'calm', 'warm']
        for palette in palettes:
            print(f"     Testing {palette} palette...")
            effects_engine.set_palette(palette)
            time.sleep(1)
        
        dmx_controller.blackout()
        time.sleep(0.5)
        dmx_controller.stop()
        
        print("✅ Effects engine test completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Effects engine test failed: {e}")
        return False

def test_integration(config):
    """Test full system integration."""
    print("\n🔗 Testing System Integration...")
    print("-" * 40)
    
    try:
        # Initialize all components
        dmx_controller = DMXController(config)
        audio_processor = AudioProcessor(config)
        effects_engine = LightEffectsEngine(config, dmx_controller)
        
        print("✅ All components initialized")
        
        # Start components
        dmx_controller.start()
        audio_processor.start()
        
        print("✅ All components started")
        print("🎉 Running integrated test for 15 seconds...")
        
        # Run for 15 seconds
        for i in range(150):  # 15 seconds at 10 FPS
            # Get real audio features
            audio_features = audio_processor.get_audio_features()
            
            # Update effects
            effects_engine.update(audio_features)
            
            # Print status every 30 frames (3 seconds)
            if i % 30 == 0:
                volume = audio_features['smoothed_volume']
                beat = "BEAT" if audio_features['beat_detected'] else "----"
                mode = effects_engine.get_status()['current_mode']
                print(f"   [{i//10:2d}s] Volume: {volume:.2f} | {beat} | Mode: {mode}")
            
            time.sleep(0.1)
        
        # Cleanup
        audio_processor.stop()
        dmx_controller.blackout()
        time.sleep(0.5)
        dmx_controller.stop()
        
        print("✅ Integration test completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

def print_system_info():
    """Print system information."""
    print("\n💻 System Information")
    print("-" * 40)
    
    # Python version
    print(f"Python: {sys.version}")
    
    # Check for required modules
    modules = [
        'numpy', 'scipy', 'librosa', 'sounddevice', 
        'yaml', 'serial', 'threading'
    ]
    
    print("\n📦 Module Availability:")
    for module in modules:
        try:
            __import__(module)
            print(f"   ✅ {module}")
        except ImportError:
            print(f"   ❌ {module} - NOT AVAILABLE")
    
    # Check for audio devices
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        print(f"\n🎵 Audio Devices: {len(devices)} found")
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                print(f"   Input:  {device['name']}")
    except Exception as e:
        print(f"\n🎵 Audio Devices: Error querying - {e}")

def main():
    """Main test function."""
    print("╔════════════════════════════════════════╗")
    print("║     Raspberry Pi DMX Light Show        ║")
    print("║           System Test Script           ║")
    print("╚════════════════════════════════════════╝")
    
    setup_logging()
    
    # Load configuration
    config = load_config()
    if not config:
        sys.exit(1)
    
    print_system_info()
    
    # Run tests
    tests = [
        ("Audio Input", test_audio_input),
        ("DMX Output", test_dmx_output),
        ("Effects Engine", test_effects_engine),
        ("System Integration", test_integration)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = test_func(config)
            results[test_name] = result
        except KeyboardInterrupt:
            print(f"\n⚠️  Test '{test_name}' interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {e}")
            results[test_name] = False
    
    # Print summary
    print("\n" + "="*50)
    print("📋 TEST SUMMARY")
    print("="*50)
    
    all_passed = True
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name:<20} : {status}")
        if not result:
            all_passed = False
    
    print("\n" + "="*50)
    if all_passed:
        print("🎉 All tests PASSED! Your system is ready for the light show!")
    else:
        print("⚠️  Some tests FAILED. Please check the errors above.")
    print("="*50)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Testing interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        sys.exit(1)

