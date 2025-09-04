"""
DMX controller module for managing Par lights via USB DMX interface.
Handles DMX512 protocol communication and light fixture control.
"""

import time
import threading
import logging
import numpy as np
from typing import Dict, List, Tuple, Optional

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    logging.warning("PySerial not available - DMX output will be simulated")

logger = logging.getLogger(__name__)

class DMXController:
    def __init__(self, config):
        self.config = config['dmx']
        self.lights_config = config['lights']['par_lights']
        
        # DMX parameters
        self.interface_port = self.config['interface']
        self.universe = self.config['universe']
        self.refresh_rate = self.config['refresh_rate']
        
        # DMX universe data (512 channels)
        self.dmx_data = [0] * 512
        
        # Light fixture tracking
        self.lights = {}
        self._initialize_lights()
        
        # Serial connection
        self.serial_connection = None
        self.running = False
        self.output_thread = None
        
        # Performance tracking
        self.last_update_time = 0
        self.frame_count = 0
        
        self._setup_dmx_interface()
    
    def _initialize_lights(self):
        """Initialize light fixture objects from configuration."""
        for light_config in self.lights_config:
            light = ParLight(light_config)
            self.lights[light.name] = light
            logger.info(f"Initialized light: {light.name} at DMX address {light.dmx_address}")
    
    def _setup_dmx_interface(self):
        """Setup DMX USB interface connection."""
        if not SERIAL_AVAILABLE:
            logger.warning("Serial not available - running in simulation mode")
            return
        
        try:
            # Common DMX USB interface settings
            self.serial_connection = serial.Serial(
                port=self.interface_port,
                baudrate=250000,  # DMX512 standard baud rate
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_TWO,
                timeout=1
            )
            logger.info(f"Connected to DMX interface at {self.interface_port}")
            
        except Exception as e:
            logger.error(f"Failed to connect to DMX interface: {e}")
            self.serial_connection = None
    
    def start(self):
        """Start DMX output thread."""
        if self.running:
            return
        
        self.running = True
        self.output_thread = threading.Thread(target=self._output_loop)
        self.output_thread.start()
        logger.info("DMX controller started")
    
    def stop(self):
        """Stop DMX output and close connections."""
        self.running = False
        
        if self.output_thread:
            self.output_thread.join()
        
        if self.serial_connection:
            self.serial_connection.close()
        
        logger.info("DMX controller stopped")
    
    def _output_loop(self):
        """Main DMX output loop."""
        frame_time = 1.0 / self.refresh_rate
        
        while self.running:
            start_time = time.time()
            
            try:
                self._send_dmx_frame()
                self.frame_count += 1
                
                # Maintain consistent frame rate
                elapsed = time.time() - start_time
                sleep_time = max(0, frame_time - elapsed)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
            except Exception as e:
                logger.error(f"Error in DMX output loop: {e}")
                time.sleep(0.1)
    
    def _send_dmx_frame(self):
        """Send current DMX data frame to interface."""
        if not self.serial_connection:
            # Simulation mode - just update timing
            self.last_update_time = time.time()
            return
        
        try:
            # DMX512 frame format:
            # Break (88µs low) + Mark After Break (8µs high) + Start Code (0x00) + 512 data bytes
            
            # Send break
            self.serial_connection.break_condition = True
            time.sleep(0.000088)  # 88 microseconds
            self.serial_connection.break_condition = False
            
            # Mark after break
            time.sleep(0.000008)  # 8 microseconds
            
            # Send start code and data
            frame_data = bytes([0x00] + self.dmx_data)
            self.serial_connection.write(frame_data)
            
            self.last_update_time = time.time()
            
        except Exception as e:
            logger.error(f"Error sending DMX frame: {e}")
    
    def set_light_rgb(self, light_name: str, red: int, green: int, blue: int, intensity: int = None):
        """Set RGB values for a specific light."""
        if light_name not in self.lights:
            logger.warning(f"Light '{light_name}' not found")
            return
        
        light = self.lights[light_name]
        
        # Clamp values to 0-255 range
        red = max(0, min(255, red))
        green = max(0, min(255, green))
        blue = max(0, min(255, blue))
        
        # Set DMX channels
        if light.channels['red']:
            self.dmx_data[light.channels['red'] - 1] = red
        if light.channels['green']:
            self.dmx_data[light.channels['green'] - 1] = green
        if light.channels['blue']:
            self.dmx_data[light.channels['blue'] - 1] = blue
        
        # Set intensity if provided and channel exists
        if intensity is not None and light.channels['intensity']:
            intensity = max(0, min(255, intensity))
            self.dmx_data[light.channels['intensity'] - 1] = intensity
        
        # Update light state
        light.current_rgb = (red, green, blue)
        if intensity is not None:
            light.current_intensity = intensity
    
    def set_light_intensity(self, light_name: str, intensity: int):
        """Set intensity for a specific light."""
        if light_name not in self.lights:
            logger.warning(f"Light '{light_name}' not found")
            return
        
        light = self.lights[light_name]
        intensity = max(0, min(255, intensity))
        
        if light.channels['intensity']:
            self.dmx_data[light.channels['intensity'] - 1] = intensity
            light.current_intensity = intensity
    
    def set_light_strobe(self, light_name: str, strobe_speed: int):
        """Set strobe speed for a specific light."""
        if light_name not in self.lights:
            logger.warning(f"Light '{light_name}' not found")
            return
        
        light = self.lights[light_name]
        strobe_speed = max(0, min(255, strobe_speed))
        
        if light.channels['strobe']:
            self.dmx_data[light.channels['strobe'] - 1] = strobe_speed
    
    def set_all_lights_rgb(self, red: int, green: int, blue: int, intensity: int = None):
        """Set RGB values for all lights."""
        for light_name in self.lights:
            self.set_light_rgb(light_name, red, green, blue, intensity)
    
    def set_all_lights_intensity(self, intensity: int):
        """Set intensity for all lights."""
        for light_name in self.lights:
            self.set_light_intensity(light_name, intensity)
    
    def blackout(self):
        """Turn off all lights."""
        self.set_all_lights_rgb(0, 0, 0, 0)
    
    def get_light_state(self, light_name: str) -> Optional[Dict]:
        """Get current state of a specific light."""
        if light_name not in self.lights:
            return None
        
        light = self.lights[light_name]
        return {
            'name': light.name,
            'dmx_address': light.dmx_address,
            'rgb': light.current_rgb,
            'intensity': light.current_intensity,
            'channels': light.channels
        }
    
    def get_all_lights_state(self) -> Dict:
        """Get current state of all lights."""
        return {name: self.get_light_state(name) for name in self.lights}
    
    def get_performance_stats(self) -> Dict:
        """Get performance statistics."""
        current_time = time.time()
        uptime = current_time - (self.last_update_time - (self.frame_count / self.refresh_rate))
        
        return {
            'frame_count': self.frame_count,
            'uptime': uptime,
            'fps': self.frame_count / uptime if uptime > 0 else 0,
            'target_fps': self.refresh_rate,
            'last_update': self.last_update_time
        }


class ParLight:
    """Represents a Par light fixture with DMX control."""
    
    def __init__(self, config):
        self.name = config['name']
        self.dmx_address = config['dmx_address']
        self.channels = config['channels']
        
        # Current state
        self.current_rgb = (0, 0, 0)
        self.current_intensity = 0
        
        # Validate channel configuration
        self._validate_channels()
    
    def _validate_channels(self):
        """Validate DMX channel configuration."""
        required_channels = ['red', 'green', 'blue']
        
        for channel in required_channels:
            if channel not in self.channels:
                logger.warning(f"Missing required channel '{channel}' for light {self.name}")
                self.channels[channel] = None
        
        # Ensure channel numbers are within valid DMX range (1-512)
        for channel_name, channel_num in self.channels.items():
            if channel_num is not None:
                if not (1 <= channel_num <= 512):
                    logger.error(f"Invalid channel number {channel_num} for {self.name}.{channel_name}")
                    self.channels[channel_name] = None
    
    def __str__(self):
        return f"ParLight({self.name}, DMX:{self.dmx_address}, RGB:{self.current_rgb}, Intensity:{self.current_intensity})"

