#!/bin/bash
# Audio Setup and Testing Script for Raspberry Pi DMX Light Show
# Configures ALSA, tests audio devices, and validates setup

set -e

echo "╔════════════════════════════════════════╗"
echo "║     Audio Setup & Testing Script       ║"
echo "║     Raspberry Pi DMX Light Show        ║"
echo "╚════════════════════════════════════════╝"
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   error "This script should not be run as root (don't use sudo)"
   exit 1
fi

# Step 1: Install required packages
log "Installing required audio packages..."
sudo apt update
sudo apt install -y libasound2-dev portaudio19-dev pulseaudio pulseaudio-utils alsa-utils

# Step 2: Restart PulseAudio
log "Restarting PulseAudio..."
pulseaudio --kill 2>/dev/null || true
sleep 2
pulseaudio --start

# Step 3: Add user to audio group
log "Adding user to audio group..."
sudo usermod -a -G audio $USER

# Step 4: Detect audio devices
log "Detecting audio devices..."
echo
echo "=== Available Playback Devices ==="
aplay -l || warn "No playback devices found"
echo
echo "=== Available Recording Devices ==="
arecord -l || warn "No recording devices found"
echo

# Step 5: Find Sound Blaster device
log "Looking for Sound Blaster device..."
SOUND_BLASTER_CARD=""
SOUND_BLASTER_DEVICE=""
SOUND_BLASTER_NAME=""

# Parse arecord output to find Sound Blaster
while IFS= read -r line; do
    if [[ $line == *"Sound Blaster"* ]] || [[ $line == *"Creative"* ]]; then
        # Extract card and device numbers
        if [[ $line =~ card\ ([0-9]+):.*device\ ([0-9]+): ]]; then
            SOUND_BLASTER_CARD="${BASH_REMATCH[1]}"
            SOUND_BLASTER_DEVICE="${BASH_REMATCH[2]}"
            SOUND_BLASTER_NAME=$(echo "$line" | sed 's/.*\[\(.*\)\].*/\1/')
            success "Found Sound Blaster: $SOUND_BLASTER_NAME"
            success "Card: $SOUND_BLASTER_CARD, Device: $SOUND_BLASTER_DEVICE"
            break
        fi
    fi
done < <(arecord -l 2>/dev/null)

if [[ -z "$SOUND_BLASTER_CARD" ]]; then
    warn "Sound Blaster device not found in recording devices"
    warn "Available recording devices:"
    arecord -l 2>/dev/null | grep "card"
    echo
    read -p "Enter card number manually (or press Enter to skip): " manual_card
    read -p "Enter device number manually (or press Enter to skip): " manual_device
    
    if [[ -n "$manual_card" && -n "$manual_device" ]]; then
        SOUND_BLASTER_CARD="$manual_card"
        SOUND_BLASTER_DEVICE="$manual_device"
        SOUND_BLASTER_NAME="Manual Selection"
    else
        error "Cannot proceed without audio device"
        exit 1
    fi
fi

ALSA_DEVICE="hw:${SOUND_BLASTER_CARD},${SOUND_BLASTER_DEVICE}"
log "Using ALSA device: $ALSA_DEVICE"

# Step 6: Configure ALSA default device
log "Configuring ALSA default device..."
cat > ~/.asoundrc << EOF
# ALSA configuration for DMX Light Show
pcm.!default {
    type hw
    card $SOUND_BLASTER_CARD
    device $SOUND_BLASTER_DEVICE
}

ctl.!default {
    type hw
    card $SOUND_BLASTER_CARD
}

# Fallback for applications that need different formats
pcm.dmix_default {
    type dmix
    ipc_key 1024
    slave {
        pcm "hw:$SOUND_BLASTER_CARD,$SOUND_BLASTER_DEVICE"
        period_time 0
        period_size 1024
        buffer_size 4096
        rate 44100
    }
    bindings {
        0 0
    }
}
EOF

success "Created ~/.asoundrc configuration"

# Step 7: Test audio recording
log "Testing audio recording..."
TEST_FILE="/tmp/lightshow_audio_test.wav"

echo "Recording 3 seconds of audio from $ALSA_DEVICE..."
echo "Please make some noise or play music during this test..."
sleep 2

if arecord -D "$ALSA_DEVICE" -f cd -c 1 -t wav -d 3 "$TEST_FILE" 2>/dev/null; then
    success "Audio recording successful!"
    
    # Check if file has content
    if [[ -f "$TEST_FILE" ]]; then
        file_size=$(stat -c%s "$TEST_FILE" 2>/dev/null || stat -f%z "$TEST_FILE" 2>/dev/null)
        if [[ $file_size -gt 44 ]]; then  # WAV header is 44 bytes
            success "Audio file contains data (${file_size} bytes)"
            
            echo "Would you like to play back the recorded audio? (y/n)"
            read -r play_response
            if [[ $play_response =~ ^[Yy]$ ]]; then
                log "Playing back recorded audio..."
                aplay "$TEST_FILE" 2>/dev/null || warn "Playback failed"
            fi
        else
            warn "Audio file is empty or corrupted"
        fi
    fi
    
    # Clean up test file
    rm -f "$TEST_FILE"
else
    error "Audio recording failed"
    echo "Trying with different parameters..."
    
    # Try different sample rates and formats
    for rate in 44100 48000 22050; do
        for channels in 1 2; do
            log "Trying ${rate}Hz, ${channels} channel(s)..."
            if arecord -D "$ALSA_DEVICE" -r "$rate" -c "$channels" -f S16_LE -t wav -d 1 "$TEST_FILE" 2>/dev/null; then
                success "Recording works with ${rate}Hz, ${channels} channel(s)"
                rm -f "$TEST_FILE"
                break 2
            fi
        done
    done
fi

# Step 8: Update config.yaml
log "Updating config.yaml with detected audio device..."
CONFIG_FILE="config.yaml"

if [[ -f "$CONFIG_FILE" ]]; then
    # Backup original config
    cp "$CONFIG_FILE" "${CONFIG_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Update device name in config
    sed -i.tmp "s/device_name: .*/device_name: \"$ALSA_DEVICE\"  # Auto-detected Sound Blaster/" "$CONFIG_FILE"
    rm -f "${CONFIG_FILE}.tmp"
    
    success "Updated $CONFIG_FILE with device: $ALSA_DEVICE"
else
    warn "config.yaml not found in current directory"
fi

# Step 9: Test Python audio access
log "Testing Python sounddevice access..."
if command -v python3 >/dev/null; then
    if python3 -c "
import sounddevice as sd
import numpy as np
try:
    devices = sd.query_devices()
    print('✓ sounddevice can query devices')
    
    # Try to find our device
    device_found = False
    for i, device in enumerate(devices):
        if '$ALSA_DEVICE' in device['name'] or 'Sound Blaster' in device['name']:
            print(f'✓ Found audio device: {device[\"name\"]}')
            device_found = True
            break
    
    if not device_found:
        print('⚠ Specific device not found, but sounddevice is working')
    
except Exception as e:
    print(f'✗ Error with sounddevice: {e}')
    exit(1)
" 2>/dev/null; then
        success "Python sounddevice test passed"
    else
        warn "Python sounddevice test failed - may need to reinstall"
        echo "Run: pip uninstall sounddevice && pip install sounddevice"
    fi
else
    warn "Python3 not found"
fi

# Step 10: Display summary
echo
echo "╔════════════════════════════════════════╗"
echo "║              SETUP SUMMARY             ║"
echo "╚════════════════════════════════════════╝"
echo
echo "Audio Device Configuration:"
echo "  Device Name: $SOUND_BLASTER_NAME"
echo "  ALSA Device: $ALSA_DEVICE"
echo "  Config File: Updated with detected device"
echo
echo "Files Created/Modified:"
echo "  ~/.asoundrc - ALSA configuration"
echo "  config.yaml - Updated with audio device"
echo
echo "Next Steps:"
echo "  1. Restart your terminal session (or run: source ~/.bashrc)"
echo "  2. Test the lightshow: python lightshow_ui.py"
echo "  3. Check for 'Audio: Connected' status in GUI"
echo "  4. Verify volume > 0 when music is playing"
echo
echo "Troubleshooting:"
echo "  - If still getting errors, try: sudo reboot"
echo "  - Check mixer levels: alsamixer"
echo "  - View detailed logs in lightshow console output"
echo

success "Audio setup completed!"
