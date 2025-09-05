#!/usr/bin/env python3
"""
Raspberry Pi DMX Light Show - Launcher Script
Provides options to run with GUI or command line interface.

Author: Generated for Raspberry Pi DMX Project
"""

import sys
import argparse
from pathlib import Path

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
    """Main launcher entry point."""
    print_banner()
    
    parser = argparse.ArgumentParser(description='DMX Light Show Controller')
    parser.add_argument('--gui', action='store_true', 
                       help='Launch with graphical user interface (default)')
    parser.add_argument('--cli', action='store_true', 
                       help='Launch with command line interface only')
    parser.add_argument('--startup', action='store_true',
                       help='Use startup script with hardware detection')
    
    args = parser.parse_args()
    
    # Check if config file exists
    if not Path('config.yaml').exists():
        print("Error: Configuration file 'config.yaml' not found!")
        print("Please create the configuration file before running.")
        sys.exit(1)
    
    # Determine which interface to use
    if args.cli:
        print("Starting with command line interface...")
        if args.startup:
            from start_lightshow import main as startup_main
            startup_main()
        else:
            from main import main as cli_main
            cli_main()
    else:
        # Default to GUI
        print("Starting with graphical user interface...")
        try:
            from lightshow_ui import main as gui_main
            gui_main()
        except ImportError as e:
            print(f"Error: Could not import GUI components: {e}")
            print("Falling back to command line interface...")
            if args.startup:
                from start_lightshow import main as startup_main
                startup_main()
            else:
                from main import main as cli_main
                cli_main()

if __name__ == "__main__":
    main()
