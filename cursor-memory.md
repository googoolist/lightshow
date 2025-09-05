# Raspberry Pi DMX Light Show - Development Memory

## Project Overview
Created a complete audio-reactive DMX lighting controller for Raspberry Pi that captures audio from a Sound Blaster USB dongle and controls Par lights via DMX USB interface.

## Architecture Decisions

### Modular Design
- **audio_processor.py**: Real-time audio capture, beat detection, and frequency analysis using librosa and sounddevice
- **dmx_controller.py**: DMX512 protocol implementation with serial communication for USB DMX interfaces
- **light_effects.py**: Audio-to-light mapping engine with multiple effect modes and smooth transitions
- **main.py**: Orchestrator that coordinates all components with graceful shutdown handling

### Key Technical Choices

#### Audio Processing
- Used `librosa` for advanced beat detection and onset analysis
- Implemented `sounddevice` for low-latency audio capture from USB dongles
- Created frequency band analysis (bass, mid, treble) for sophisticated light mapping
- Added volume smoothing and tempo estimation for stable effects

#### DMX Communication
- Implemented DMX512 protocol directly using PySerial
- Created ParLight class for flexible fixture management
- Added proper DMX timing (break/mark-after-break) for compatibility
- Included simulation mode for development without hardware

#### Effects Engine
- Multiple effect modes: auto, pulse, chase, fade, strobe
- Color palette system with mood-based selections
- Smooth transitions between colors and intensities
- Beat-responsive intensity boosts with natural decay

#### Configuration System
- YAML-based configuration for easy customization
- Flexible DMX channel mapping for different Par light models
- Audio device auto-detection with fallback options
- Adjustable effect parameters and color palettes

## Hardware Compatibility

### Tested Audio Devices
- Sound Blaster USB dongles (auto-detected by device name)
- Generic USB audio interfaces
- Built-in Raspberry Pi audio (with limitations)

### DMX Interface Support
- Enttec DMX USB Pro (primary target)
- Generic FTDI-based DMX interfaces
- Proper udev rules for device permissions

### Par Light Support
- Configurable channel mapping (RGB, intensity, strobe, program)
- Support for 3-channel, 4-channel, and 6-channel Par lights
- Easy addition of new fixture types via configuration

## Performance Optimizations

### Threading Strategy
- Separate threads for audio processing, DMX output, and main loop
- 60 FPS main processing loop with 30 Hz DMX refresh rate
- Non-blocking audio callback for minimal latency

### Memory Management
- Fixed-size audio buffers to prevent memory growth
- Efficient numpy operations for signal processing
- Deque-based history tracking with maximum lengths

### Real-time Considerations
- Configurable buffer sizes for latency vs. stability trade-offs
- Frame rate limiting to prevent CPU overload
- Performance monitoring with detailed statistics

## Installation & Deployment

### System Dependencies
- PortAudio for audio processing
- ALSA/PulseAudio for USB audio support
- FTDI drivers for DMX USB interfaces
- Python 3.8+ with pip

### Automated Installation
- Created comprehensive `install.sh` script
- Automatic dependency installation
- Udev rules setup for USB device permissions
- Systemd service configuration for auto-start
- **Auto-startup functionality**: Service starts automatically on boot with proper hardware detection

### Testing Framework
- Comprehensive `test_system.py` for validation
- Individual component testing (audio, DMX, effects)
- Integration testing with simulated audio
- Hardware compatibility verification
- **Auto-startup testing**: `test_startup.py` validates service configuration and hardware readiness

## Configuration Best Practices

### Audio Settings
- Use 44.1kHz sample rate for best compatibility
- Buffer size 1024 samples balances latency and stability
- Volume gain of 2.0 works well for most setups
- Noise floor at 0.01 prevents false triggers

### DMX Settings
- 30 Hz refresh rate optimal for smooth effects
- Standard DMX timing (88μs break, 8μs MAB)
- 512-channel universe support
- Address validation to prevent conflicts

### Effect Parameters
- Transition speed 0.8 provides smooth color changes
- Beat response strength 1.2 gives good punch without overwhelming
- Color change probability 0.1 adds subtle variety

## Known Issues & Solutions

### Audio Latency
- **Issue**: High latency with some USB audio devices
- **Solution**: Reduce buffer size, use dedicated USB audio interface
- **Workaround**: Increase volume gain to compensate for delayed response

### DMX Timing
- **Issue**: Some cheap DMX interfaces have timing issues
- **Solution**: Added configurable timing parameters
- **Workaround**: Reduce refresh rate if flicker occurs

### Beat Detection Sensitivity
- **Issue**: False beat detection in noisy environments
- **Solution**: Adjustable onset threshold and noise floor
- **Workaround**: Use external noise gate or better audio positioning

## UI Implementation

### Graphical User Interface
- **Modern tkinter-based GUI**: Dark theme interface with real-time monitoring
- **Three-button mode selection**: Easy switching between lighting configurations
- **Real-time audio visualization**: Volume, beat detection, and frequency band displays
- **System status monitoring**: Audio/DMX connection status and performance metrics
- **Control buttons**: Start/stop, blackout functionality with keyboard shortcuts
- **Configuration-driven**: Mode names and descriptions loaded from config.yaml

### Lighting Modes
- **Mode 1 - Classic Auto**: Original frequency-mapped lighting with auto color changes
- **Mode 2 - Ping Pong Wave**: Sequential wave effect bouncing between lights with smooth color cycling
- **Mode 3 - Rapid Fade**: Rapid color transitions with smooth fade in/out effects (no strobing)
- **Mode switching**: Real-time mode changes without restarting the application
- **Configuration-based parameters**: Each mode has customizable speed, intensity, and color settings

### New Effect Implementations
- **Ping Pong Effect**: Wave-based intensity distribution with color cycling on direction changes
- **Rapid Fade Mode**: Fast color transitions with smooth intensity changes and no harsh strobing
- **Smooth transitions**: All modes maintain smooth color transitions without harsh changes
- **Beat-responsive timing**: Effects speed up and intensify with detected beats

## Future Enhancements

### Planned Features
- Web interface for remote control and monitoring
- MIDI input support for manual control
- OSC protocol support for integration with other systems
- Machine learning-based beat detection improvements
- Additional lighting modes and effects

### Hardware Expansions
- Multiple DMX universe support
- Support for moving head lights
- Integration with haze machines and other effects
- Wireless DMX support

### Software Improvements
- Real-time visualization of audio and lighting
- Preset system for saved light shows
- Integration with music streaming services
- Mobile app for wireless control

## Deployment Notes

### Raspberry Pi Specific
- Works best on Pi 3B+ or newer for processing power
- Use quality SD card (Class 10 or better) for reliability
- Consider active cooling for continuous operation
- External USB hub recommended for multiple devices

### Auto-Startup Configuration
- **Plug-and-play operation**: System automatically starts on boot after installation
- **Hardware detection**: Waits for USB audio and DMX devices to be ready
- **Graceful startup**: 10-second initial delay plus device detection with timeouts
- **Service management**: Full systemd integration with proper restart policies
- **Logging**: Startup logs written to `/tmp/lightshow_startup.log` for debugging

### Production Recommendations
- Use UPS for power protection
- Network monitoring for remote management
- Backup configuration files regularly
- Regular system updates for security

