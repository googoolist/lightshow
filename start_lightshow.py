#!/usr/bin/env python3
"""
Startup script for Raspberry Pi DMX Light Show
Handles hardware detection and graceful startup for auto-boot scenarios.

Author: Generated for Raspberry Pi DMX Project
"""

import time
import sys
import subprocess
import logging
import yaml
from pathlib import Path
import sounddevice as sd
import serial.tools.list_ports

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/lightshow_startup.log')
    ]
)
logger = logging.getLogger(__name__)

def wait_for_audio_devices(max_wait=60, target_device="Sound Blaster"):
    """Wait for audio devices to be available."""
    logger.info(f"Waiting for audio device containing '{target_device}'...")
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            devices = sd.query_devices()
            for device in devices:
                if target_device.lower() in device['name'].lower() and device['max_input_channels'] > 0:
                    logger.info(f"Found audio device: {device['name']}")
                    return True
            
            logger.info("Audio device not found, waiting...")
            time.sleep(2)
            
        except Exception as e:
            logger.warning(f"Error checking audio devices: {e}")
            time.sleep(2)
    
    logger.warning(f"Timeout waiting for audio device '{target_device}'")
    # Continue anyway - might work with default device
    return False

def wait_for_dmx_interface(max_wait=30, target_port="/dev/ttyUSB0"):
    """Wait for DMX USB interface to be available."""
    logger.info(f"Waiting for DMX interface at {target_port}...")
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            # Check if the specific device exists
            if Path(target_port).exists():
                logger.info(f"Found DMX interface at {target_port}")
                return True
            
            # Also check for any FTDI devices
            ports = serial.tools.list_ports.comports()
            for port in ports:
                if "FTDI" in str(port.description).upper() or "DMX" in str(port.description).upper():
                    logger.info(f"Found potential DMX interface: {port.device} - {port.description}")
                    return True
            
            logger.info("DMX interface not found, waiting...")
            time.sleep(2)
            
        except Exception as e:
            logger.warning(f"Error checking DMX interface: {e}")
            time.sleep(2)
    
    logger.warning(f"Timeout waiting for DMX interface")
    # Continue anyway - simulation mode might be enabled
    return False

def check_system_readiness():
    """Check if the system is ready for audio processing."""
    logger.info("Checking system readiness...")
    
    # Wait for audio system to be ready
    for attempt in range(10):
        try:
            # Try to initialize audio system
            sd.query_devices()
            logger.info("Audio system is ready")
            break
        except Exception as e:
            logger.warning(f"Audio system not ready (attempt {attempt + 1}): {e}")
            time.sleep(3)
    
    # Check if PulseAudio is running (common on Pi)
    try:
        result = subprocess.run(['pulseaudio', '--check'], capture_output=True)
        if result.returncode == 0:
            logger.info("PulseAudio is running")
        else:
            logger.info("PulseAudio not running, attempting to start...")
            subprocess.run(['pulseaudio', '--start'], capture_output=True)
            time.sleep(2)
    except Exception as e:
        logger.warning(f"Could not check/start PulseAudio: {e}")

def load_config():
    """Load configuration to check device settings."""
    try:
        with open('config.yaml', 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Could not load config.yaml: {e}")
        return None

def main():
    """Main startup routine."""
    logger.info("=== DMX Light Show Startup Script ===")
    
    # Wait a bit for system to fully boot
    logger.info("Waiting for system to stabilize...")
    time.sleep(5)
    
    # Load configuration
    config = load_config()
    if not config:
        logger.error("Cannot proceed without configuration")
        sys.exit(1)
    
    # Get device settings from config
    audio_device = config.get('audio', {}).get('device_name', 'Sound Blaster')
    dmx_interface = config.get('dmx', {}).get('interface', '/dev/ttyUSB0')
    
    # Check system readiness
    check_system_readiness()
    
    # Wait for hardware devices
    audio_ready = wait_for_audio_devices(target_device=audio_device)
    dmx_ready = wait_for_dmx_interface(target_port=dmx_interface)
    
    if not audio_ready:
        logger.warning("Audio device not detected - continuing with default device")
    
    if not dmx_ready:
        logger.warning("DMX interface not detected - will run in simulation mode")
    
    # Final delay to ensure everything is stable
    logger.info("Hardware checks complete, starting main application...")
    time.sleep(2)
    
    # Start the main application
    try:
        from main import main as lightshow_main
        lightshow_main()
    except Exception as e:
        logger.error(f"Failed to start light show: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
