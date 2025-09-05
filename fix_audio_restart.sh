#!/bin/bash
# Fix audio system after Raspberry Pi restart

echo "=== Fixing Audio System After Restart ==="

# Stop any conflicting audio services
echo "Stopping conflicting audio services..."
sudo systemctl stop pulseaudio 2>/dev/null || true
systemctl --user stop pulseaudio 2>/dev/null || true
systemctl --user stop pipewire 2>/dev/null || true
systemctl --user stop pipewire-pulse 2>/dev/null || true

sleep 2

# Restart audio services in correct order
echo "Restarting audio services..."
sudo systemctl restart alsa-state
sleep 1

# Start Pipewire services
echo "Starting Pipewire..."
systemctl --user start pipewire
sleep 1
systemctl --user start pipewire-pulse
sleep 2

# Check if Sound Blaster is detected
echo "Checking Sound Blaster detection..."
if arecord -l | grep -i "sound blaster\|creative\|s3"; then
    echo "✓ Sound Blaster detected"
else
    echo "⚠ Sound Blaster not detected, please check USB connection"
fi

# Test basic audio recording
echo "Testing audio recording..."
if timeout 2 arecord -D hw:2,0 -f S16_LE -r 44100 -c 2 -d 1 /tmp/test_audio.wav 2>/dev/null; then
    echo "✓ Audio recording test passed"
    rm -f /tmp/test_audio.wav
else
    echo "⚠ Audio recording test failed"
fi

# Check Python audio
echo "Testing Python sounddevice..."
cd ~/lightshow
source venv/bin/activate

python3 -c "
import os
import sounddevice as sd
import numpy as np

# Force environment
os.environ['SD_ENABLE_PULSE'] = '0'

try:
    print('Available devices:')
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            print(f'  {i}: {device[\"name\"]} (inputs: {device[\"max_input_channels\"]})')
    
    # Test recording with device 2
    print('Testing recording with device 2...')
    test_data = sd.rec(int(0.5 * 44100), samplerate=44100, channels=2, device=2, dtype=np.float32, blocking=True)
    print('✓ Python audio test passed')
    
except Exception as e:
    print(f'✗ Python audio test failed: {e}')
"

echo ""
echo "=== Audio System Ready ==="
echo "You can now run: python lightshow_ui.py"
