
# Raspberry Pi DMX Light Show

A real-time audio-reactive DMX lighting controller for Raspberry Pi that creates dynamic light shows synchronized to music from a Sound Blaster USB dongle.

## Features

- **Real-time Audio Processing**: Captures audio from Sound Blaster USB dongle
- **Beat Detection**: Advanced algorithm to detect beats and rhythm patterns
- **Volume Analysis**: Dynamic response to audio volume levels
- **DMX Control**: Full DMX512 protocol support via USB interface
- **Par Light Support**: Optimized for Par light fixtures
- **Smooth Transitions**: Interpolated lighting effects for seamless shows
- **Configurable**: Easy setup for different light configurations

## Hardware Requirements

- Raspberry Pi (3B+ or newer recommended)
- Sound Blaster USB audio dongle
- DMX USB interface (e.g., Enttec DMX USB Pro)
- Par lights with DMX capability
- DMX cables
- Audio source (microphone, line input, etc.)

## Software Requirements

- Raspberry Pi OS (Bullseye or newer)
- Python 3.8+
- USB audio drivers
- DMX USB interface drivers

## Installation

### Automatic Installation

1. Clone this repository to your Raspberry Pi
2. Run the installation script:
   ```bash
   chmod +x install.sh
   ./install.sh
   ```
3. **Reboot your Raspberry Pi** (required for group permissions)
4. Connect your hardware:
   - Sound Blaster dongle to USB port
   - DMX USB interface to USB port
   - Connect Par lights to DMX interface with proper addressing
5. Configure your setup in `config.yaml`
6. The light show will now **start automatically on boot**!

### Manual Installation

1. Clone this repository to your Raspberry Pi
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Connect your hardware and configure `config.yaml`
4. Run the application:
   ```bash
   python main.py
   ```

## Configuration

Edit `config.yaml` to match your setup:
- Audio device settings
- DMX universe and channel mappings
- Light fixture definitions
- Effect parameters

## Auto-Startup Management

After installation, the light show is configured to start automatically when you boot your Raspberry Pi. 

### Service Commands

```bash
# Start the service manually
sudo systemctl start dmx-lightshow

# Stop the service
sudo systemctl stop dmx-lightshow

# Disable auto-startup
sudo systemctl disable dmx-lightshow

# Enable auto-startup
sudo systemctl enable dmx-lightshow

# View real-time logs
sudo journalctl -u dmx-lightshow -f

# View startup logs
tail -f /tmp/lightshow_startup.log
```

### Testing Auto-Startup

Run the test script to verify your configuration:
```bash
./test_startup.py
```

This will check all requirements for successful auto-startup.

## Usage

The application runs in real-time, continuously processing audio input and generating corresponding DMX output to control your Par lights. The system automatically detects beats and adjusts lighting intensity based on volume levels.

### Plug and Play Operation

1. **Power on** your Raspberry Pi
2. **Wait** for boot sequence (about 30-60 seconds)
3. **Connect audio source** and play music
4. **Enjoy** your automated light show!

The system will automatically:
- Wait for USB devices to be ready
- Detect your Sound Blaster audio device
- Connect to the DMX interface
- Start processing audio and controlling lights

## Troubleshooting

- Ensure proper permissions for USB devices
- Check DMX addressing matches your light fixtures
- Verify audio input levels
- Monitor console output for debugging information

