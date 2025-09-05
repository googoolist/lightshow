
# Raspberry Pi DMX Light Show

A real-time audio-reactive DMX lighting controller for Raspberry Pi that creates dynamic light shows synchronized to music from a Sound Blaster USB dongle.

## Features

- **Real-time Audio Processing**: Captures audio from Sound Blaster USB dongle
- **Beat Detection**: Advanced algorithm to detect beats and rhythm patterns
- **Volume Analysis**: Dynamic response to audio volume levels
- **DMX Control**: Full DMX512 protocol support via USB interface
- **Par Light Support**: Optimized for RGBW Par light fixtures with 10-channel DMX
- **Smooth Transitions**: Interpolated lighting effects for seamless shows
- **Graphical User Interface**: Modern dark-themed GUI with real-time monitoring
- **Multiple Lighting Modes**: Three distinct lighting configurations with smooth switching
- **Configurable**: Easy setup for different light configurations and effects

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
   # Launch with GUI (recommended)
   python lightshow_launcher.py
   
   # Or launch GUI directly
   python lightshow_ui.py
   
   # Or command line only
   python lightshow_launcher.py --cli
   
   # Or original main script
   python main.py
   ```

## Configuration

Edit `config.yaml` to match your setup:
- Audio device settings
- DMX universe and channel mappings
- Light fixture definitions
- Effect parameters
- Lighting mode configurations

## Lighting Modes

The application includes three configurable lighting modes accessible via the GUI:

### Mode 1: Classic Auto
- **Description**: Original auto-reactive lighting with frequency mapping
- **Behavior**: Maps different frequency bands (bass, mid, treble) to different lights
- **Color Changes**: Automatic based on tempo and volume
- **Best For**: General music listening and background ambiance

### Mode 2: Ping Pong Wave
- **Description**: Sequential light ping pong effect with smooth color cycling
- **Behavior**: Creates a wave effect that bounces between lights 1 and 4, cycling through colors
- **Color Changes**: Smooth color transitions after each oscillation
- **Best For**: Rhythmic music with strong beats

### Mode 3: Rapid Fade
- **Description**: Rapid color transitions with smooth fade in/out effects
- **Behavior**: Very frequent color changes with smooth intensity variations (no strobing)
- **Color Changes**: Rapid, smooth color transitions every 0.3 seconds with beat-responsive intensity
- **Best For**: High-energy music where you want dynamic colors without harsh flashing

### Customizing Modes

Each mode can be customized in `config.yaml` under the `lighting_modes` section:
- `name`: Display name in the UI
- `description`: Description shown under each button
- `effect_mode`: The lighting algorithm to use
- `palette`: Color palette selection
- `transition_speed`: How quickly colors transition
- `beat_response_strength`: Intensity of beat responses
- `color_change_probability`: Frequency of automatic color changes

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

