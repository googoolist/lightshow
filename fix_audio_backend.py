#!/usr/bin/env python3
"""
Script to test and fix audio backend issues on Raspberry Pi with Pipewire
"""

import os
import sys
import subprocess

def stop_conflicting_services():
    """Stop PulseAudio if it's running and interfering"""
    print("Stopping any conflicting audio services...")
    try:
        subprocess.run(['sudo', 'systemctl', 'stop', 'pulseaudio'], capture_output=True)
        subprocess.run(['systemctl', '--user', 'stop', 'pulseaudio'], capture_output=True)
        print("✓ Stopped PulseAudio services")
    except:
        pass

def start_pipewire():
    """Ensure Pipewire is running"""
    print("Starting Pipewire services...")
    try:
        subprocess.run(['systemctl', '--user', 'start', 'pipewire'], check=True)
        subprocess.run(['systemctl', '--user', 'start', 'pipewire-pulse'], check=True)
        print("✓ Started Pipewire services")
    except subprocess.CalledProcessError as e:
        print(f"⚠ Error starting Pipewire: {e}")

def test_audio_backends():
    """Test what audio backends are available"""
    print("\nTesting audio backends...")
    
    # Set environment to force ALSA
    os.environ['SD_ENABLE_PULSE'] = '0'
    os.environ['ALSA_PCM_CARD'] = 'default'
    os.environ['ALSA_PCM_DEVICE'] = '0'
    
    try:
        import sounddevice as sd
        print("✓ sounddevice imported successfully")
        
        # List host APIs
        print("\nAvailable host APIs:")
        hostapis = sd.query_hostapis()
        for i, api in enumerate(hostapis):
            print(f"  {i}: {api['name']} ({'default' if api['default_input_device'] >= 0 else 'no input'})")
        
        # Try to set ALSA as default
        try:
            for i, api in enumerate(hostapis):
                if 'ALSA' in api['name']:
                    sd.default.hostapi = i
                    print(f"✓ Set ALSA (index {i}) as default host API")
                    break
        except Exception as e:
            print(f"⚠ Could not set ALSA as default: {e}")
        
        # List devices
        print("\nAvailable audio devices:")
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                default_str = " (DEFAULT)" if i == sd.default.device[0] else ""
                print(f"  {i}: {device['name']} (inputs: {device['max_input_channels']}){default_str}")
        
        # Test recording
        print("\nTesting audio recording...")
        import numpy as np
        
        # Try recording for 1 second
        duration = 1.0
        sample_rate = 44100
        
        try:
            print("Recording test audio...")
            audio_data = sd.rec(int(duration * sample_rate), 
                              samplerate=sample_rate, 
                              channels=2, 
                              dtype=np.float32)
            sd.wait()
            
            # Check if we got audio
            max_level = np.max(np.abs(audio_data))
            print(f"✓ Recording successful! Max level: {max_level:.4f}")
            
            if max_level < 0.001:
                print("⚠ Very low audio level - check your input source")
            else:
                print("✓ Audio levels look good!")
                
        except Exception as e:
            print(f"✗ Recording failed: {e}")
            return False
            
    except ImportError as e:
        print(f"✗ Could not import sounddevice: {e}")
        return False
    except Exception as e:
        print(f"✗ Audio backend test failed: {e}")
        return False
    
    return True

def main():
    print("=== Raspberry Pi Audio Backend Fixer ===\n")
    
    stop_conflicting_services()
    start_pipewire()
    
    # Wait a moment for services to start
    import time
    time.sleep(2)
    
    success = test_audio_backends()
    
    if success:
        print("\n✓ Audio backend is working! You can now run the lightshow.")
        print("\nTo run the lightshow:")
        print("  cd ~/lightshow")
        print("  source venv/bin/activate") 
        print("  python lightshow_ui.py")
    else:
        print("\n✗ Audio backend issues detected.")
        print("\nTry running:")
        print("  sudo apt update && sudo apt install -y pipewire pipewire-pulse pipewire-alsa")
        print("  systemctl --user restart pipewire pipewire-pulse")

if __name__ == "__main__":
    main()
