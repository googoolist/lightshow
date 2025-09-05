#!/usr/bin/env python3
"""
Raspberry Pi DMX Light Show - GUI Interface
Modern UI for controlling lighting modes and real-time monitoring.

Author: Generated for Raspberry Pi DMX Project
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import yaml
import logging
from pathlib import Path
import sys

# Import our modules
from main import LightShowController
from light_effects import LightEffectsEngine

logger = logging.getLogger(__name__)

class LightShowUI:
    """Modern GUI interface for the light show controller."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("DMX Light Show Control")
        self.root.geometry("800x600")
        self.root.configure(bg='#2b2b2b')
        
        # Application state
        self.controller = None
        self.running = False
        self.current_mode = "mode_1"
        self.config = self._load_config()
        self.lighting_modes = self.config.get('lighting_modes', {})
        
        # UI update thread
        self.ui_update_thread = None
        self.stop_ui_updates = False
        
        # Setup UI
        self._setup_styles()
        self._create_widgets()
        self._setup_bindings()
        
        # Update display
        self._update_mode_buttons()
        
        logger.info("Light Show UI initialized")
    
    def _load_config(self):
        """Load configuration from YAML file."""
        try:
            with open('config.yaml', 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            messagebox.showerror("Config Error", f"Could not load config.yaml: {e}")
            return {}
    
    def _setup_styles(self):
        """Setup modern dark theme styles."""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors for dark theme
        style.configure('Title.TLabel', 
                       background='#2b2b2b', 
                       foreground='#ffffff', 
                       font=('Arial', 18, 'bold'))
        
        style.configure('Subtitle.TLabel',
                       background='#2b2b2b',
                       foreground='#cccccc',
                       font=('Arial', 12))
        
        style.configure('Status.TLabel',
                       background='#2b2b2b',
                       foreground='#00ff00',
                       font=('Arial', 10, 'bold'))
        
        style.configure('ModeButton.TButton',
                       background='#404040',
                       foreground='#ffffff',
                       borderwidth=2,
                       font=('Arial', 12, 'bold'),
                       padding=10)
        
        style.map('ModeButton.TButton',
                 background=[('active', '#505050'),
                           ('pressed', '#606060')])
        
        style.configure('ActiveMode.TButton',
                       background='#0066cc',
                       foreground='#ffffff',
                       borderwidth=3,
                       font=('Arial', 12, 'bold'),
                       padding=10)
        
        style.configure('Control.TButton',
                       background='#006600',
                       foreground='#ffffff',
                       font=('Arial', 11, 'bold'),
                       padding=5)
        
        style.map('Control.TButton',
                 background=[('active', '#008800')])
        
        style.configure('Stop.TButton',
                       background='#cc0000',
                       foreground='#ffffff',
                       font=('Arial', 11, 'bold'),
                       padding=5)
        
        style.map('Stop.TButton',
                 background=[('active', '#ee0000')])
    
    def _create_widgets(self):
        """Create and layout all UI widgets."""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_frame, 
                               text="🎵 DMX Light Show Controller 💡", 
                               style='Title.TLabel')
        title_label.pack(pady=(0, 20))
        
        # Status section
        self._create_status_section(main_frame)
        
        # Mode selection section
        self._create_mode_section(main_frame)
        
        # Control buttons section
        self._create_control_section(main_frame)
        
        # Audio visualization section
        self._create_audio_section(main_frame)
    
    def _create_status_section(self, parent):
        """Create status display section."""
        status_frame = ttk.LabelFrame(parent, text="System Status", padding=10)
        status_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Status indicators
        self.status_label = ttk.Label(status_frame, 
                                     text="● STOPPED", 
                                     style='Status.TLabel',
                                     foreground='#ff0000')
        self.status_label.pack(anchor=tk.W)
        
        self.audio_status = ttk.Label(status_frame, 
                                     text="Audio: Not Connected", 
                                     style='Subtitle.TLabel')
        self.audio_status.pack(anchor=tk.W)
        
        self.dmx_status = ttk.Label(status_frame, 
                                   text="DMX: Not Connected", 
                                   style='Subtitle.TLabel')
        self.dmx_status.pack(anchor=tk.W)
        
        self.mode_status = ttk.Label(status_frame, 
                                    text=f"Current Mode: {self.current_mode}", 
                                    style='Subtitle.TLabel')
        self.mode_status.pack(anchor=tk.W)
    
    def _create_mode_section(self, parent):
        """Create mode selection buttons."""
        mode_frame = ttk.LabelFrame(parent, text="Lighting Modes", padding=15)
        mode_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Create grid for mode buttons
        self.mode_buttons = {}
        
        for i, (mode_id, mode_config) in enumerate(self.lighting_modes.items()):
            button_frame = ttk.Frame(mode_frame)
            button_frame.grid(row=0, column=i, padx=10, pady=10, sticky="ew")
            
            # Mode button
            btn = ttk.Button(button_frame,
                           text=mode_config.get('name', f'Mode {i+1}'),
                           style='ModeButton.TButton',
                           command=lambda m=mode_id: self._set_mode(m))
            btn.pack(fill=tk.X, pady=(0, 5))
            
            # Mode description
            desc_label = ttk.Label(button_frame,
                                 text=mode_config.get('description', ''),
                                 style='Subtitle.TLabel',
                                 wraplength=200,
                                 justify=tk.CENTER)
            desc_label.pack()
            
            self.mode_buttons[mode_id] = btn
            
            # Configure grid weights
            mode_frame.grid_columnconfigure(i, weight=1)
    
    def _create_control_section(self, parent):
        """Create control buttons."""
        control_frame = ttk.LabelFrame(parent, text="Controls", padding=10)
        control_frame.pack(fill=tk.X, pady=(0, 20))
        
        button_frame = ttk.Frame(control_frame)
        button_frame.pack()
        
        self.start_button = ttk.Button(button_frame,
                                      text="▶ Start Light Show",
                                      style='Control.TButton',
                                      command=self._start_lightshow)
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(button_frame,
                                     text="⏹ Stop Light Show",
                                     style='Stop.TButton',
                                     command=self._stop_lightshow,
                                     state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.blackout_button = ttk.Button(button_frame,
                                         text="⚫ Blackout",
                                         style='Control.TButton',
                                         command=self._blackout)
        self.blackout_button.pack(side=tk.LEFT)
    
    def _create_audio_section(self, parent):
        """Create audio visualization section."""
        audio_frame = ttk.LabelFrame(parent, text="Audio Monitor", padding=10)
        audio_frame.pack(fill=tk.BOTH, expand=True)
        
        # Audio level indicators
        self.volume_label = ttk.Label(audio_frame, 
                                     text="Volume: 0%", 
                                     style='Subtitle.TLabel')
        self.volume_label.pack(anchor=tk.W)
        
        self.beat_label = ttk.Label(audio_frame, 
                                   text="Beat: ●", 
                                   style='Subtitle.TLabel')
        self.beat_label.pack(anchor=tk.W)
        
        self.tempo_label = ttk.Label(audio_frame, 
                                    text="Tempo: 0 BPM", 
                                    style='Subtitle.TLabel')
        self.tempo_label.pack(anchor=tk.W)
        
        # Progress bars for frequency bands
        self.bass_var = tk.DoubleVar()
        self.mid_var = tk.DoubleVar()
        self.treble_var = tk.DoubleVar()
        
        ttk.Label(audio_frame, text="Bass:", style='Subtitle.TLabel').pack(anchor=tk.W, pady=(10, 0))
        self.bass_bar = ttk.Progressbar(audio_frame, variable=self.bass_var, maximum=100)
        self.bass_bar.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(audio_frame, text="Mid:", style='Subtitle.TLabel').pack(anchor=tk.W)
        self.mid_bar = ttk.Progressbar(audio_frame, variable=self.mid_var, maximum=100)
        self.mid_bar.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(audio_frame, text="Treble:", style='Subtitle.TLabel').pack(anchor=tk.W)
        self.treble_bar = ttk.Progressbar(audio_frame, variable=self.treble_var, maximum=100)
        self.treble_bar.pack(fill=tk.X)
    
    def _setup_bindings(self):
        """Setup keyboard shortcuts and window events."""
        self.root.bind('<KeyPress-1>', lambda e: self._set_mode('mode_1'))
        self.root.bind('<KeyPress-2>', lambda e: self._set_mode('mode_2'))
        self.root.bind('<KeyPress-3>', lambda e: self._set_mode('mode_3'))
        self.root.bind('<space>', lambda e: self._toggle_lightshow())
        self.root.bind('<KeyPress-b>', lambda e: self._blackout())
        
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _update_mode_buttons(self):
        """Update mode button styles based on current selection."""
        for mode_id, button in self.mode_buttons.items():
            if mode_id == self.current_mode:
                button.configure(style='ActiveMode.TButton')
            else:
                button.configure(style='ModeButton.TButton')
    
    def _set_mode(self, mode_id):
        """Set the current lighting mode."""
        if mode_id in self.lighting_modes:
            self.current_mode = mode_id
            self._update_mode_buttons()
            self.mode_status.configure(text=f"Current Mode: {self.lighting_modes[mode_id]['name']}")
            
            # Apply mode to running controller
            if self.controller and self.running:
                self._apply_mode_to_controller(mode_id)
            
            logger.info(f"Selected mode: {mode_id}")
    
    def _apply_mode_to_controller(self, mode_id):
        """Apply the selected mode configuration to the running controller."""
        try:
            mode_config = self.lighting_modes[mode_id]
            
            if self.controller and self.controller.effects_engine:
                # Update effects engine parameters
                effects = self.controller.effects_engine
                
                effects.set_mode(mode_config.get('effect_mode', 'auto'))
                effects.set_palette(mode_config.get('palette', 'energetic'))
                effects.transition_speed = mode_config.get('transition_speed', 0.8)
                effects.beat_response_strength = mode_config.get('beat_response_strength', 1.2)
                effects.color_change_probability = mode_config.get('color_change_probability', 0.1)
                effects.intensity_multiplier = mode_config.get('intensity_multiplier', 0.9)
                
                # Store special mode parameters
                if hasattr(effects, 'ping_pong_speed'):
                    effects.ping_pong_speed = mode_config.get('ping_pong_speed', 2.0)
                if hasattr(effects, 'flash_intensity'):
                    effects.flash_intensity = mode_config.get('flash_intensity', 1.5)
                
                logger.info(f"Applied mode {mode_id} to running controller")
                
        except Exception as e:
            logger.error(f"Error applying mode {mode_id}: {e}")
    
    def _start_lightshow(self):
        """Start the light show in a separate thread."""
        if not self.running:
            self.running = True
            self.start_button.configure(state=tk.DISABLED)
            self.stop_button.configure(state=tk.NORMAL)
            self.status_label.configure(text="● STARTING...", foreground='#ffaa00')
            
            # Start controller in separate thread
            controller_thread = threading.Thread(target=self._run_controller, daemon=True)
            controller_thread.start()
            
            # Start UI update thread
            self.stop_ui_updates = False
            self.ui_update_thread = threading.Thread(target=self._update_ui_loop, daemon=True)
            self.ui_update_thread.start()
    
    def _run_controller(self):
        """Run the light show controller."""
        try:
            self.controller = LightShowController()
            
            # Apply current mode before starting
            self._apply_mode_to_controller(self.current_mode)
            
            success = self.controller.start()
            
            if not success:
                self.root.after(0, lambda: self._handle_controller_error("Failed to start controller"))
                
        except Exception as e:
            self.root.after(0, lambda: self._handle_controller_error(f"Controller error: {e}"))
    
    def _handle_controller_error(self, error_msg):
        """Handle controller errors in the main thread."""
        self.running = False
        self.start_button.configure(state=tk.NORMAL)
        self.stop_button.configure(state=tk.DISABLED)
        self.status_label.configure(text="● ERROR", foreground='#ff0000')
        messagebox.showerror("Light Show Error", error_msg)
    
    def _stop_lightshow(self):
        """Stop the light show."""
        if self.running:
            self.running = False
            self.stop_ui_updates = True
            
            if self.controller:
                self.controller.stop()
                self.controller = None
            
            self.start_button.configure(state=tk.NORMAL)
            self.stop_button.configure(state=tk.DISABLED)
            self.status_label.configure(text="● STOPPED", foreground='#ff0000')
            
            # Reset status displays
            self.audio_status.configure(text="Audio: Not Connected")
            self.dmx_status.configure(text="DMX: Not Connected")
            self._reset_audio_displays()
    
    def _toggle_lightshow(self):
        """Toggle light show on/off."""
        if self.running:
            self._stop_lightshow()
        else:
            self._start_lightshow()
    
    def _blackout(self):
        """Trigger blackout."""
        if self.controller and self.controller.dmx_controller:
            self.controller.dmx_controller.blackout()
    
    def _update_ui_loop(self):
        """Update UI elements in a loop."""
        while not self.stop_ui_updates and self.running:
            try:
                if self.controller:
                    status = self.controller.get_status()
                    self.root.after(0, lambda: self._update_displays(status))
                
                time.sleep(0.1)  # Update every 100ms
                
            except Exception as e:
                logger.error(f"Error in UI update loop: {e}")
                break
    
    def _update_displays(self, status):
        """Update all display elements with current status."""
        try:
            # Update main status
            if status.get('running', False):
                self.status_label.configure(text="● RUNNING", foreground='#00ff00')
            
            # Update audio status
            audio_data = status.get('audio', {})
            if audio_data:
                self.audio_status.configure(text="Audio: Connected")
                
                volume = audio_data.get('smoothed_volume', 0) * 100
                self.volume_label.configure(text=f"Volume: {volume:.0f}%")
                
                beat = audio_data.get('beat_detected', False)
                beat_color = '#00ff00' if beat else '#666666'
                self.beat_label.configure(text="Beat: ●", foreground=beat_color)
                
                tempo = audio_data.get('tempo', 0)
                self.tempo_label.configure(text=f"Tempo: {tempo:.0f} BPM")
                
                # Update frequency bars
                freq_powers = audio_data.get('frequency_powers', {})
                self.bass_var.set(freq_powers.get('bass', 0) * 100)
                self.mid_var.set(freq_powers.get('mid', 0) * 100)
                self.treble_var.set(freq_powers.get('treble', 0) * 100)
            
            # Update DMX status
            dmx_data = status.get('dmx', {})
            if dmx_data:
                self.dmx_status.configure(text="DMX: Connected")
            
        except Exception as e:
            logger.error(f"Error updating displays: {e}")
    
    def _reset_audio_displays(self):
        """Reset audio display elements."""
        self.volume_label.configure(text="Volume: 0%")
        self.beat_label.configure(text="Beat: ●", foreground='#666666')
        self.tempo_label.configure(text="Tempo: 0 BPM")
        self.bass_var.set(0)
        self.mid_var.set(0)
        self.treble_var.set(0)
    
    def _on_closing(self):
        """Handle window closing event."""
        if self.running:
            self._stop_lightshow()
        
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        """Start the GUI main loop."""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self._on_closing()


def main():
    """Main entry point for the UI."""
    # Setup logging for UI
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Check if config file exists
    if not Path('config.yaml').exists():
        messagebox.showerror("Configuration Error", 
                           "config.yaml not found!\nPlease ensure the configuration file exists.")
        sys.exit(1)
    
    # Create and run UI
    app = LightShowUI()
    app.run()


if __name__ == "__main__":
    main()
