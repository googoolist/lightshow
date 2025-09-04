#!/usr/bin/env python3
"""
Raspberry Pi DMX Light Show - Main Application
Audio-reactive lighting controller for Par lights via DMX USB interface.

Author: Generated for Raspberry Pi DMX Project
"""

import time
import signal
import sys
import logging
import yaml
import threading
from pathlib import Path

# Import our modules
from audio_processor import AudioProcessor
from dmx_controller import DMXController
from light_effects import LightEffectsEngine

# Configuration
CONFIG_FILE = 'config.yaml'
LOG_FILE = 'lightshow.log'

class LightShowController:
    """Main controller class that coordinates all components."""
    
    def __init__(self, config_file=CONFIG_FILE):
        self.config = self._load_config(config_file)
        self.running = False
        
        # Setup logging
        self._setup_logging()
        
        # Initialize components
        self.audio_processor = None
        self.dmx_controller = None
        self.effects_engine = None
        
        # Performance monitoring
        self.frame_count = 0
        self.start_time = 0
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("Light Show Controller initialized")
    
    def _load_config(self, config_file):
        """Load configuration from YAML file."""
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            print(f"Loaded configuration from {config_file}")
            return config
        except FileNotFoundError:
            print(f"Configuration file {config_file} not found!")
            sys.exit(1)
        except yaml.YAMLError as e:
            print(f"Error parsing configuration file: {e}")
            sys.exit(1)
    
    def _setup_logging(self):
        """Setup logging configuration."""
        log_level = getattr(logging, self.config['system']['log_level'], logging.INFO)
        
        # Create logger
        global logger
        logger = logging.getLogger(__name__)
        logger.setLevel(log_level)
        
        # Create formatters
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler
        file_handler = logging.FileHandler(LOG_FILE)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Set up other module loggers
        for module_name in ['audio_processor', 'dmx_controller', 'light_effects']:
            module_logger = logging.getLogger(module_name)
            module_logger.setLevel(log_level)
            module_logger.addHandler(console_handler)
            module_logger.addHandler(file_handler)
    
    def _signal_handler(self, sig, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {sig}, shutting down...")
        self.stop()
        sys.exit(0)
    
    def initialize(self):
        """Initialize all components."""
        try:
            logger.info("Initializing components...")
            
            # Initialize DMX controller first
            logger.info("Initializing DMX controller...")
            self.dmx_controller = DMXController(self.config)
            
            # Initialize audio processor
            logger.info("Initializing audio processor...")
            self.audio_processor = AudioProcessor(self.config)
            
            # Initialize effects engine
            logger.info("Initializing effects engine...")
            self.effects_engine = LightEffectsEngine(self.config, self.dmx_controller)
            
            logger.info("All components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            return False
    
    def start(self):
        """Start the light show."""
        if not self.initialize():
            logger.error("Failed to initialize, cannot start")
            return False
        
        logger.info("Starting light show...")
        self.running = True
        self.start_time = time.time()
        
        try:
            # Start components
            self.dmx_controller.start()
            self.audio_processor.start()
            
            # Main processing loop
            self._main_loop()
            
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            return False
        
        return True
    
    def stop(self):
        """Stop the light show."""
        logger.info("Stopping light show...")
        self.running = False
        
        # Stop components
        if self.audio_processor:
            self.audio_processor.stop()
        
        if self.dmx_controller:
            # Blackout before stopping
            self.dmx_controller.blackout()
            time.sleep(0.1)
            self.dmx_controller.stop()
        
        logger.info("Light show stopped")
    
    def _main_loop(self):
        """Main processing loop."""
        logger.info("Entering main processing loop")
        
        # Performance monitoring
        last_stats_time = time.time()
        stats_interval = 10.0  # Print stats every 10 seconds
        
        try:
            while self.running:
                loop_start = time.time()
                
                # Get audio features
                if self.audio_processor and self.audio_processor.is_running():
                    audio_features = self.audio_processor.get_audio_features()
                    
                    # Update effects
                    if self.effects_engine:
                        self.effects_engine.update(audio_features)
                    
                    # Performance monitoring
                    if self.config['system']['performance_monitoring']:
                        self.frame_count += 1
                        
                        # Print stats periodically
                        if time.time() - last_stats_time >= stats_interval:
                            self._print_performance_stats(audio_features)
                            last_stats_time = time.time()
                
                # Maintain target frame rate (60 FPS)
                target_frame_time = 1.0 / 60.0
                elapsed = time.time() - loop_start
                sleep_time = max(0, target_frame_time - elapsed)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        
        logger.info("Exited main processing loop")
    
    def _print_performance_stats(self, audio_features):
        """Print performance and status information."""
        uptime = time.time() - self.start_time
        fps = self.frame_count / uptime if uptime > 0 else 0
        
        # Audio stats
        volume = audio_features.get('smoothed_volume', 0)
        beat = audio_features.get('beat_detected', False)
        tempo = audio_features.get('tempo', 0)
        
        # DMX stats
        dmx_stats = self.dmx_controller.get_performance_stats() if self.dmx_controller else {}
        dmx_fps = dmx_stats.get('fps', 0)
        
        # Effects stats
        effects_status = self.effects_engine.get_status() if self.effects_engine else {}
        current_mode = effects_status.get('current_mode', 'unknown')
        current_palette = effects_status.get('current_palette', 'unknown')
        
        logger.info(
            f"Performance - FPS: {fps:.1f}, DMX FPS: {dmx_fps:.1f}, "
            f"Volume: {volume:.2f}, Beat: {beat}, Tempo: {tempo:.0f}, "
            f"Mode: {current_mode}, Palette: {current_palette}"
        )
    
    def get_status(self):
        """Get comprehensive system status."""
        status = {
            'running': self.running,
            'uptime': time.time() - self.start_time if self.start_time else 0,
            'frame_count': self.frame_count
        }
        
        if self.audio_processor:
            status['audio'] = self.audio_processor.get_audio_features()
        
        if self.dmx_controller:
            status['dmx'] = self.dmx_controller.get_performance_stats()
            status['lights'] = self.dmx_controller.get_all_lights_state()
        
        if self.effects_engine:
            status['effects'] = self.effects_engine.get_status()
        
        return status


def print_banner():
    """Print application banner."""
    banner = """
    ╔════════════════════════════════════════╗
    ║     Raspberry Pi DMX Light Show        ║
    ║     Audio-Reactive Lighting Control    ║
    ╚════════════════════════════════════════╝
    """
    print(banner)


def main():
    """Main entry point."""
    print_banner()
    
    # Check if config file exists
    if not Path(CONFIG_FILE).exists():
        print(f"Error: Configuration file '{CONFIG_FILE}' not found!")
        print("Please create the configuration file before running.")
        sys.exit(1)
    
    # Create and start the light show controller
    controller = LightShowController()
    
    try:
        success = controller.start()
        if not success:
            print("Failed to start light show")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        controller.stop()
    
    print("Light show terminated")


if __name__ == "__main__":
    main()

