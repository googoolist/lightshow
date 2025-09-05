#!/usr/bin/env python3
"""
Audio debugging script for DMX Light Show
Tests sounddevice configuration and device detection
"""

import sounddevice as sd
import numpy as np
import time
import yaml

def test_audio_devices():
    """Test and display all audio devices"""
    print("=== Audio Device Debug ===")
    print()
    
    try:
        devices = sd.query_devices()
        print(f"Found {len(devices)} audio devices:")
        print()
        
        for i, device in enumerate(devices):
            is_default_input = (i == sd.default.device[0])
            is_default_output = (i == sd.default.device[1])
            
            default_markers = []
            if is_default_input:
                default_markers.append("DEFAULT INPUT")
            if is_default_output:
                default_markers.append("DEFAULT OUTPUT")
            
            default_str = f" ({', '.join(default_markers)})" if default_markers else ""
            
            print(f"Device {i}: {device['name']}{default_str}")
            print(f"  Max input channels: {device['max_input_channels']}")
            print(f"  Max output channels: {device['max_output_channels']}")
            print(f"  Default sample rate: {device['default_samplerate']}")
            print()
            
    except Exception as e:
        print(f"Error querying devices: {e}")
        return False
    
    return True

def test_device_recording(device_name=None, channels=2, samplerate=44100):
    """Test recording from a specific device"""
    print(f"=== Testing Recording ===")
    print(f"Device: {device_name or 'default'}")
    print(f"Channels: {channels}")
    print(f"Sample rate: {samplerate}")
    print()
    
    try:
        # Find device ID if name provided
        device_id = None
        if device_name and device_name != "default":
            devices = sd.query_devices()
            for i, device in enumerate(devices):
                if device_name.lower() in device['name'].lower():
                    device_id = i
                    print(f"Found device ID {i} for '{device_name}': {device['name']}")
                    break
            
            if device_id is None:
                print(f"Device '{device_name}' not found, using default")
        
        print("Recording 3 seconds of audio...")
        print("Make some noise or play music now!")
        
        # Record audio
        duration = 3.0
        recording = sd.rec(
            int(duration * samplerate), 
            samplerate=samplerate, 
            channels=channels,
            device=device_id,
            dtype='float64'
        )
        sd.wait()
        
        # Analyze recording
        if recording is not None and len(recording) > 0:
            # Convert to mono if stereo
            if len(recording.shape) > 1 and recording.shape[1] > 1:
                mono_audio = np.mean(recording, axis=1)
            else:
                mono_audio = recording.flatten()
            
            # Calculate levels
            rms_level = np.sqrt(np.mean(mono_audio**2))
            peak_level = np.max(np.abs(mono_audio))
            
            print(f"✓ Recording successful!")
            print(f"  RMS level: {rms_level:.6f}")
            print(f"  Peak level: {peak_level:.6f}")
            print(f"  Samples: {len(mono_audio)}")
            
            if rms_level > 0.001:
                print(f"  ✓ Good audio levels detected")
                return True, rms_level
            elif rms_level > 0.000001:
                print(f"  ⚠ Very low audio levels")
                return True, rms_level
            else:
                print(f"  ✗ No audio detected (silence)")
                return True, 0.0
        else:
            print(f"✗ Recording failed - no data returned")
            return False, 0.0
            
    except Exception as e:
        print(f"✗ Recording error: {e}")
        return False, 0.0

def test_config_device():
    """Test the device specified in config.yaml"""
    print("=== Testing Config Device ===")
    
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        audio_config = config.get('audio', {})
        device_name = audio_config.get('device_name', 'default')
        sample_rate = audio_config.get('sample_rate', 44100)
        channels = audio_config.get('input_channels', 2)
        
        print(f"Config device: {device_name}")
        print(f"Config sample rate: {sample_rate}")
        print(f"Config channels: {channels}")
        print()
        
        return test_device_recording(device_name, channels, sample_rate)
        
    except FileNotFoundError:
        print("config.yaml not found")
        return False, 0.0
    except Exception as e:
        print(f"Error reading config: {e}")
        return False, 0.0

def main():
    print("╔════════════════════════════════════════╗")
    print("║        Audio Debug Tool                ║")
    print("║        DMX Light Show                  ║")
    print("╚════════════════════════════════════════╝")
    print()
    
    # Test 1: List all devices
    if not test_audio_devices():
        print("Failed to query audio devices")
        return
    
    # Test 2: Test default device
    print()
    success, level = test_device_recording()
    
    # Test 3: Test config device
    print()
    config_success, config_level = test_config_device()
    
    # Test 4: Try Sound Blaster specifically
    print()
    print("=== Testing Sound Blaster Specifically ===")
    sb_success, sb_level = test_device_recording("Sound Blaster", 2, 44100)
    
    # Summary
    print()
    print("╔════════════════════════════════════════╗")
    print("║             SUMMARY                    ║")
    print("╚════════════════════════════════════════╝")
    print(f"Default device:      {'✓' if success else '✗'} (level: {level:.6f})")
    print(f"Config device:       {'✓' if config_success else '✗'} (level: {config_level:.6f})")
    print(f"Sound Blaster:       {'✓' if sb_success else '✗'} (level: {sb_level:.6f})")
    print()
    
    if max(level, config_level, sb_level) > 0.001:
        print("✓ Audio is working! The issue might be in the lightshow app.")
        print("  Try running: python lightshow_ui.py")
    elif max(level, config_level, sb_level) > 0.000001:
        print("⚠ Audio is working but levels are very low.")
        print("  Check input volume levels with: pavucontrol")
    else:
        print("✗ No audio detected on any device.")
        print("  Check that music is playing and microphone isn't muted")
    
    print()
    print("Troubleshooting:")
    print("  - Check input levels: pavucontrol")
    print("  - Set default device: pactl set-default-source DEVICE_NAME")
    print("  - List sources: pactl list sources short")

if __name__ == "__main__":
    main()
