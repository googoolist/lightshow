# Hardware Setup Guide

## Required Components

### Core Components
1. **Raspberry Pi** (3B+ or newer recommended)
   - Minimum 1GB RAM
   - MicroSD card (32GB+ Class 10)
   - Power supply (2.5A minimum)

2. **Sound Blaster USB Audio Dongle**
   - Creative Sound Blaster Play! 3
   - Creative Sound Blaster X-Fi Go! Pro
   - Or compatible USB audio interface with line input

3. **DMX USB Interface**
   - Enttec DMX USB Pro (recommended)
   - DMX King ultraDMX Micro
   - Generic FTDI-based DMX interface

4. **Par Lights**
   - RGB Par lights with DMX support
   - 3, 4, or 6-channel modes supported
   - Individual DMX addressing required

5. **DMX Cables**
   - 3-pin XLR or 5-pin XLR (depending on lights)
   - 120Ω termination resistor for last fixture
   - Proper DMX cable (not audio cable)

## Hardware Connections

### Audio Setup
```
Audio Source → Sound Blaster Dongle → Raspberry Pi USB
```

**Audio Sources:**
- DJ mixer line output
- Audio interface output
- Direct instrument connection
- Microphone (for ambient sound)

### DMX Chain
```
Raspberry Pi → DMX USB Interface → Par Light 1 → Par Light 2 → ... → Terminator
```

**Important:**
- Use proper DMX cables (impedance matched)
- Install 120Ω termination resistor at the last fixture
- Keep DMX runs under 1000 feet total
- Avoid running DMX cables parallel to power cables

## Raspberry Pi Setup

### OS Installation
1. Download Raspberry Pi OS Lite (64-bit recommended)
2. Flash to SD card using Raspberry Pi Imager
3. Enable SSH in boot partition (create empty 'ssh' file)
4. Configure WiFi if needed (wpa_supplicant.conf)

### Initial Configuration
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Configure audio
sudo raspi-config
# Advanced Options → Audio → Force 3.5mm jack (if using onboard audio as backup)

# Enable required interfaces
sudo raspi-config
# Interface Options → Enable I2C, SPI if needed for future expansion
```

## USB Device Configuration

### Audio Device Setup
```bash
# Check available audio devices
aplay -l
arecord -l

# Test audio input
arecord -D hw:1,0 -f cd test.wav
# Record for 5 seconds, then Ctrl+C

# Test playback
aplay test.wav
```

### DMX Interface Setup
```bash
# Check USB devices
lsusb

# Look for FTDI device (common for DMX interfaces)
# Should see something like: "Future Technology Devices International, Ltd FT232 Serial (UART) IC"

# Check serial devices
ls -la /dev/ttyUSB*
# Should show /dev/ttyUSB0 or similar
```

## Par Light Configuration

### DMX Addressing
Set each Par light to a unique DMX address using the fixture's menu:
- Light 1: Address 1 (channels 1-6)
- Light 2: Address 7 (channels 7-12)  
- Light 3: Address 13 (channels 13-18)
- Light 4: Address 19 (channels 19-24)

### Channel Modes
Configure lights for appropriate channel mode:

**3-Channel Mode (RGB):**
- Channel 1: Red
- Channel 2: Green
- Channel 3: Blue

**4-Channel Mode (RGB + Dimmer):**
- Channel 1: Red
- Channel 2: Green
- Channel 3: Blue
- Channel 4: Master Dimmer

**6-Channel Mode (Full Control):**
- Channel 1: Red
- Channel 2: Green
- Channel 3: Blue
- Channel 4: Master Dimmer
- Channel 5: Strobe/Flash
- Channel 6: Program/Auto

## Troubleshooting

### Audio Issues
**No sound detected:**
- Check USB audio device connection
- Verify device appears in `arecord -l`
- Test with `arecord` command
- Check audio levels and gain settings
- Ensure audio source is connected and playing

**High latency:**
- Reduce buffer size in config.yaml
- Use dedicated USB 2.0 port (not hub)
- Close unnecessary applications
- Consider faster SD card

### DMX Issues
**Lights not responding:**
- Check DMX cable connections
- Verify DMX addresses match configuration
- Test with DMX termination resistor
- Check for DMX cable damage
- Ensure proper cable impedance (120Ω)

**Flickering lights:**
- Add/check DMX termination resistor
- Reduce DMX refresh rate in config
- Check for electrical interference
- Verify DMX cable quality

### Performance Issues
**Choppy effects:**
- Increase audio buffer size
- Reduce DMX refresh rate
- Close unnecessary services
- Use faster SD card (Class 10+ required)
- Ensure adequate power supply

**System lag:**
- Monitor CPU usage with `htop`
- Reduce effect complexity
- Lower frame rate in config
- Consider Pi 4 for better performance

## Power Considerations

### Raspberry Pi Power
- Use quality 2.5A+ power supply
- Consider UPS for continuous operation
- Monitor voltage with `vcgencmd get_throttled`

### Light Power
- Ensure adequate power for all Par lights
- Use proper electrical distribution
- Ground all equipment properly
- Consider power consumption in venue planning

## Cable Management

### Best Practices
- Keep audio and power cables separated
- Use cable ties and management systems
- Label all cables for easy identification
- Carry spare cables for gigs
- Test all connections before events

### Portable Setup
- Use road cases for equipment protection
- Create quick-setup documentation
- Pre-configure all settings
- Test complete setup before transport

## Safety Considerations

### Electrical Safety
- Use GFCI protection in wet environments
- Properly ground all equipment
- Inspect cables regularly for damage
- Never modify electrical equipment improperly

### Heat Management
- Ensure Raspberry Pi ventilation
- Monitor system temperature
- Consider active cooling for continuous use
- Keep lights away from flammable materials

### Professional Installation
- Follow local electrical codes
- Use licensed electrician for permanent installations
- Document all connections and configurations
- Provide emergency shutdown procedures

