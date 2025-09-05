#!/usr/bin/env python3
"""
Debug script to find the correct audio device for the Sound Blaster
"""

import os
import sounddevice as sd

# Force ALSA backend
os.environ['SD_ENABLE_PULSE'] = '0'

def main():
    print("=== Audio Device Debug ===\n")
    
    try:
        # Force ALSA
        sd.default.hostapi = 'ALSA'
        print("✓ Forced ALSA backend")
    except:
        print("⚠ Could not force ALSA backend")
    
    print("\nHost APIs:")
    hostapis = sd.query_hostapis()
    for i, api in enumerate(hostapis):
        print(f"  {i}: {api['name']}")
    
    print("\nAll Audio Devices:")
    devices = sd.query_devices()
    
    sound_blaster_devices = []
    
    for i, device in enumerate(devices):
        device_name = device['name'].lower()
        inputs = device['max_input_channels']
        
        # Mark potential Sound Blaster devices
        is_sb = any(term in device_name for term in ['sound blaster', 'creative', 'blaster', 's3'])
        marker = " *** SOUND BLASTER ***" if is_sb else ""
        
        print(f"  Device {i}: {device['name']}")
        print(f"    Inputs: {inputs}, Outputs: {device['max_output_channels']}")
        print(f"    Default Sample Rate: {device['default_samplerate']}")
        print(f"    Host API: {device['hostapi']}{marker}")
        
        if is_sb and inputs > 0:
            sound_blaster_devices.append(i)
        
        print()
    
    if sound_blaster_devices:
        print(f"Found Sound Blaster devices at indices: {sound_blaster_devices}")
        
        # Test each Sound Blaster device
        import numpy as np
        for device_id in sound_blaster_devices:
            device = devices[device_id]
            print(f"\nTesting device {device_id}: {device['name']}")
            
            try:
                # Test recording for 0.5 seconds
                audio_data = sd.rec(int(0.5 * 44100), 
                                  samplerate=44100, 
                                  channels=min(2, device['max_input_channels']),
                                  device=device_id,
                                  dtype=np.float32)
                sd.wait()
                
                max_level = np.max(np.abs(audio_data))
                print(f"✓ Recording successful! Max level: {max_level:.4f}")
                print(f"  --> Use device_id: {device_id} in config")
                
            except Exception as e:
                print(f"✗ Recording failed: {e}")
    else:
        print("⚠ No Sound Blaster devices found")
        print("\nTrying default device...")
        try:
            import numpy as np
            audio_data = sd.rec(int(0.5 * 44100), samplerate=44100, channels=2)
            sd.wait()
            max_level = np.max(np.abs(audio_data))
            print(f"✓ Default device works! Max level: {max_level:.4f}")
            print("  --> Use device_name: 'default' in config")
        except Exception as e:
            print(f"✗ Default device failed: {e}")

if __name__ == "__main__":
    main()
