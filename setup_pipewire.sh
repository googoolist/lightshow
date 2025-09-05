#!/bin/bash
# Pipewire Setup Script for Raspberry Pi DMX Light Show
# Configures Pipewire to work with Sound Blaster and tests audio

set -e

echo "╔════════════════════════════════════════╗"
echo "║     Pipewire Setup Script              ║"
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

# Step 1: Start Pipewire services
log "Starting Pipewire services..."
systemctl --user start pipewire pipewire-pulse wireplumber 2>/dev/null || true
sleep 3

# Step 2: Check Pipewire status
log "Checking Pipewire status..."
if systemctl --user is-active --quiet pipewire; then
    success "Pipewire is running"
else
    warn "Pipewire is not running, attempting to start..."
    systemctl --user start pipewire
    sleep 2
fi

if systemctl --user is-active --quiet pipewire-pulse; then
    success "Pipewire-pulse is running"
else
    warn "Pipewire-pulse is not running, attempting to start..."
    systemctl --user start pipewire-pulse
    sleep 2
fi

if systemctl --user is-active --quiet wireplumber; then
    success "Wireplumber is running"
else
    warn "Wireplumber is not running, attempting to start..."
    systemctl --user start wireplumber
    sleep 2
fi

# Step 3: List Pipewire devices
log "Listing available Pipewire audio devices..."
echo
echo "=== Pipewire Audio Sources ==="
if command -v pw-cli >/dev/null; then
    pw-cli list-objects Node | grep -A5 -B5 "media.class.*Audio/Source" || warn "No audio sources found"
else
    warn "pw-cli not found, installing pipewire-utils..."
    sudo apt install -y pipewire-utils 2>/dev/null || true
fi

echo
echo "=== PulseAudio/Pipewire Devices ==="
if command -v pactl >/dev/null; then
    pactl list sources short
else
    warn "pactl not found"
fi

# Step 4: Find Sound Blaster in Pipewire
log "Looking for Sound Blaster in Pipewire devices..."
SOUND_BLASTER_FOUND=""
if command -v pactl >/dev/null; then
    SOUND_BLASTER_DEVICE=$(pactl list sources | grep -B5 -A10 -i "sound.*blaster\|creative" | grep "Name:" | head -1 | awk '{print $2}' || true)
    
    if [[ -n "$SOUND_BLASTER_DEVICE" ]]; then
        success "Found Sound Blaster device: $SOUND_BLASTER_DEVICE"
        SOUND_BLASTER_FOUND="yes"
        
        # Set as default input device
        log "Setting Sound Blaster as default input device..."
        pactl set-default-source "$SOUND_BLASTER_DEVICE" || warn "Could not set default source"
        
        # Show device details
        echo "Device details:"
        pactl list sources | grep -A20 "Name: $SOUND_BLASTER_DEVICE"
    else
        warn "Sound Blaster not found in Pipewire devices"
    fi
fi

# Step 5: Test audio recording with Pipewire
log "Testing audio recording with Pipewire..."
TEST_FILE="/tmp/pipewire_audio_test.wav"

echo "Recording 3 seconds using Pipewire default device..."
echo "Please make some noise or play music during this test..."
sleep 2

# Try recording with parecord (Pipewire/PulseAudio)
if command -v parecord >/dev/null; then
    if parecord --format=s16le --rate=44100 --channels=2 --file-format=wav "$TEST_FILE" &
    then
        RECORD_PID=$!
        sleep 3
        kill $RECORD_PID 2>/dev/null || true
        wait $RECORD_PID 2>/dev/null || true
        
        if [[ -f "$TEST_FILE" ]]; then
            file_size=$(stat -c%s "$TEST_FILE" 2>/dev/null || stat -f%z "$TEST_FILE" 2>/dev/null)
            if [[ $file_size -gt 44 ]]; then
                success "Pipewire recording successful! (${file_size} bytes)"
                
                echo "Would you like to play back the recorded audio? (y/n)"
                read -r play_response
                if [[ $play_response =~ ^[Yy]$ ]]; then
                    log "Playing back recorded audio..."
                    paplay "$TEST_FILE" 2>/dev/null || aplay "$TEST_FILE" 2>/dev/null || warn "Playback failed"
                fi
            else
                warn "Recording file is empty or corrupted"
            fi
            rm -f "$TEST_FILE"
        else
            error "Recording failed - no file created"
        fi
    else
        error "Failed to start parecord"
    fi
else
    # Fallback to arecord with default device
    warn "parecord not found, trying arecord with default device..."
    if arecord -f cd -c 2 -t wav -d 3 "$TEST_FILE" 2>/dev/null; then
        success "Recording with arecord successful!"
        rm -f "$TEST_FILE"
    else
        error "Recording failed with both parecord and arecord"
    fi
fi

# Step 6: Test Python sounddevice with Pipewire
log "Testing Python sounddevice with Pipewire..."
if command -v python3 >/dev/null; then
    python3 -c "
import sounddevice as sd
import numpy as np
try:
    print('Available audio devices:')
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            default_marker = ' (DEFAULT)' if i == sd.default.device[0] else ''
            print(f'  {i}: {device[\"name\"]} - {device[\"max_input_channels\"]} inputs{default_marker}')
    
    print('')
    print('Testing default input device...')
    
    # Try a short recording test
    duration = 1.0  # seconds
    samplerate = 44100
    channels = 2
    
    print(f'Recording {duration}s test with {channels} channels at {samplerate}Hz...')
    recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=channels, dtype='float64')
    sd.wait()
    
    # Check if we got audio data
    level = np.abs(recording).mean()
    print(f'Average audio level: {level:.6f}')
    
    if level > 0.0001:
        print('✓ Python sounddevice can record audio successfully!')
    else:
        print('⚠ Python sounddevice working but getting very low/no audio')
        print('  Try playing music and running this test again')
    
except Exception as e:
    print(f'✗ Error with Python sounddevice: {e}')
    exit(1)
"
    if [[ $? -eq 0 ]]; then
        success "Python sounddevice test completed"
    else
        error "Python sounddevice test failed"
    fi
else
    warn "Python3 not found"
fi

# Step 7: Update config.yaml
log "Updating config.yaml for Pipewire..."
if [[ -f "config.yaml" ]]; then
    cp "config.yaml" "config.yaml.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Update to use default device (Pipewire managed)
    sed -i.tmp 's/device_name: .*/device_name: "default"  # Pipewire default device/' config.yaml
    sed -i.tmp 's/input_channels: .*/input_channels: 2  # Stereo input/' config.yaml
    rm -f config.yaml.tmp
    
    success "Updated config.yaml for Pipewire"
else
    warn "config.yaml not found"
fi

# Step 8: Display summary
echo
echo "╔════════════════════════════════════════╗"
echo "║           PIPEWIRE SETUP SUMMARY       ║"
echo "╚════════════════════════════════════════╝"
echo
echo "Pipewire Configuration:"
echo "  Services: $(systemctl --user is-active pipewire pipewire-pulse wireplumber | tr '\n' ' ')"
if [[ -n "$SOUND_BLASTER_FOUND" ]]; then
    echo "  Sound Blaster: Found and set as default"
    echo "  Default Device: $SOUND_BLASTER_DEVICE"
else
    echo "  Sound Blaster: Using system default device"
fi
echo "  Config File: Updated to use 'default' device"
echo
echo "Next Steps:"
echo "  1. Test the lightshow: python lightshow_ui.py"
echo "  2. Check for 'Audio: Connected' status in GUI"
echo "  3. Verify volume > 0 when music is playing"
echo "  4. Check beat detection works with music"
echo
echo "Troubleshooting:"
echo "  - If no audio: Check input levels with 'pavucontrol'"
echo "  - If wrong device: Run 'pactl set-default-source DEVICE_NAME'"
echo "  - View Pipewire status: 'systemctl --user status pipewire'"
echo

success "Pipewire setup completed!"
