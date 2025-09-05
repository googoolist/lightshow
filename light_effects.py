"""
Light effects engine that maps audio features to DMX lighting effects.
Creates smooth, responsive light shows synchronized to music.
"""

import numpy as np
import time
import random
import math
import logging
from typing import Dict, List, Tuple, Optional
from collections import deque

logger = logging.getLogger(__name__)

class LightEffectsEngine:
    def __init__(self, config, dmx_controller):
        self.config = config
        self.effects_config = config['effects']
        self.dmx_controller = dmx_controller
        
        # Color palettes
        self.color_palettes = self.effects_config['color_palettes']
        self.current_palette = 'energetic'
        
        # Effect parameters
        self.transition_speed = self.effects_config['transition_speed']
        self.intensity_multiplier = self.effects_config['intensity_multiplier']
        self.beat_response_strength = self.effects_config['beat_response_strength']
        self.color_change_probability = self.effects_config['color_change_probability']
        
        # State tracking
        self.current_colors = {}  # Per-light current colors
        self.target_colors = {}   # Per-light target colors
        self.base_intensity = 0.5
        self.beat_intensity_boost = 0.0
        self.last_beat_time = 0
        
        # Effect modes
        self.current_mode = 'auto'
        self.mode_start_time = time.time()
        
        # Audio feature history for smoothing
        self.volume_history = deque(maxlen=10)
        self.beat_history = deque(maxlen=5)
        
        # Initialize light states
        self._initialize_light_states()
        
        # Color cycling
        self.color_cycle_position = 0
        self.color_cycle_speed = 0.02
        
        # Ping pong effect state
        self.ping_pong_position = 0.0
        self.ping_pong_direction = 1
        self.ping_pong_speed = 2.0
        self.ping_pong_color_index = 0
        
        # Flash storm effect state
        self.flash_intensity = 1.5
        self.flash_random_timer = 0
        self.flash_color_timer = 0
        
        logger.info("Light effects engine initialized")
    
    def _initialize_light_states(self):
        """Initialize color states for all lights."""
        light_states = self.dmx_controller.get_all_lights_state()
        
        for light_name in light_states:
            self.current_colors[light_name] = [0, 0, 0]
            self.target_colors[light_name] = [0, 0, 0]
    
    def update(self, audio_features: Dict):
        """Update lighting effects based on audio features."""
        try:
            # Update audio feature history
            self.volume_history.append(audio_features['smoothed_volume'])
            self.beat_history.append(audio_features['beat_detected'])
            
            # Determine effect mode based on audio characteristics
            self._update_effect_mode(audio_features)
            
            # Calculate base intensity from volume
            self._update_base_intensity(audio_features)
            
            # Handle beat responses
            self._handle_beat_response(audio_features)
            
            # Update colors based on current mode
            self._update_colors(audio_features)
            
            # Apply smooth transitions
            self._apply_color_transitions()
            
            # Send colors to DMX controller
            self._output_to_dmx()
            
        except Exception as e:
            logger.error(f"Error updating light effects: {e}")
    
    def _update_effect_mode(self, audio_features: Dict):
        """Determine and update the current effect mode based on audio."""
        tempo = audio_features['tempo']
        avg_volume = np.mean(list(self.volume_history)) if self.volume_history else 0
        
        # Auto-select palette based on music characteristics
        if tempo > 140 and avg_volume > 0.6:
            self.current_palette = 'energetic'
        elif tempo < 80 and avg_volume < 0.3:
            self.current_palette = 'calm'
        elif avg_volume > 0.4:
            self.current_palette = 'warm'
        
        # Change mode periodically for variety
        time_in_mode = time.time() - self.mode_start_time
        if time_in_mode > 30:  # Change mode every 30 seconds
            if random.random() < 0.3:  # 30% chance to change
                self._change_effect_mode()
    
    def _change_effect_mode(self):
        """Change to a new effect mode."""
        modes = ['auto', 'pulse', 'chase', 'strobe', 'fade', 'ping_pong', 'flash_storm']
        self.current_mode = random.choice([m for m in modes if m != self.current_mode])
        self.mode_start_time = time.time()
        logger.info(f"Changed effect mode to: {self.current_mode}")
    
    def _update_base_intensity(self, audio_features: Dict):
        """Update base intensity based on volume."""
        volume = audio_features['smoothed_volume']
        
        # Map volume to intensity with some minimum
        self.base_intensity = np.clip(
            volume * self.intensity_multiplier + 0.1,
            0.1, 1.0
        )
    
    def _handle_beat_response(self, audio_features: Dict):
        """Handle lighting responses to detected beats."""
        if audio_features['beat_detected']:
            self.last_beat_time = time.time()
            
            # Beat intensity boost
            beat_strength = audio_features.get('beat_strength', 1.0)
            self.beat_intensity_boost = min(beat_strength * self.beat_response_strength, 0.5)
            
            # Chance to change colors on beat
            if random.random() < self.color_change_probability:
                self._trigger_color_change(audio_features)
        else:
            # Decay beat intensity boost
            time_since_beat = time.time() - self.last_beat_time
            decay_rate = 3.0  # Decay over 3 seconds
            self.beat_intensity_boost *= max(0, 1 - (time_since_beat / decay_rate))
    
    def _trigger_color_change(self, audio_features: Dict):
        """Trigger a color change effect."""
        palette = self.color_palettes[self.current_palette]
        
        if self.current_mode == 'auto':
            # Random color assignment
            for light_name in self.target_colors:
                self.target_colors[light_name] = random.choice(palette).copy()
        
        elif self.current_mode == 'chase':
            # Sequential color chase
            light_names = list(self.target_colors.keys())
            for i, light_name in enumerate(light_names):
                color_index = (i + int(time.time() * 2)) % len(palette)
                self.target_colors[light_name] = palette[color_index].copy()
        
        elif self.current_mode == 'pulse':
            # All lights same color
            color = random.choice(palette)
            for light_name in self.target_colors:
                self.target_colors[light_name] = color.copy()
    
    def _update_colors(self, audio_features: Dict):
        """Update target colors based on current mode and audio features."""
        palette = self.color_palettes[self.current_palette]
        freq_powers = audio_features['frequency_powers']
        
        if self.current_mode == 'auto':
            self._update_auto_mode(palette, freq_powers)
        elif self.current_mode == 'pulse':
            self._update_pulse_mode(palette, audio_features)
        elif self.current_mode == 'chase':
            self._update_chase_mode(palette, audio_features)
        elif self.current_mode == 'fade':
            self._update_fade_mode(palette, audio_features)
        elif self.current_mode == 'strobe':
            self._update_strobe_mode(palette, audio_features)
        elif self.current_mode == 'ping_pong':
            self._update_ping_pong_mode(palette, audio_features)
        elif self.current_mode == 'flash_storm':
            self._update_flash_storm_mode(palette, audio_features)
    
    def _update_auto_mode(self, palette: List, freq_powers: Dict):
        """Auto mode: Map frequency bands to different lights."""
        light_names = list(self.target_colors.keys())
        
        # Map frequency bands to color intensity
        bass_power = freq_powers.get('bass', 0)
        mid_power = freq_powers.get('mid', 0)
        treble_power = freq_powers.get('treble', 0)
        
        # Normalize powers
        max_power = max(bass_power, mid_power, treble_power, 0.1)
        bass_ratio = bass_power / max_power
        mid_ratio = mid_power / max_power
        treble_ratio = treble_power / max_power
        
        # Assign colors based on frequency content
        for i, light_name in enumerate(light_names):
            if i % 3 == 0:  # Bass lights
                intensity = bass_ratio
                base_color = [255, 0, 0]  # Red for bass
            elif i % 3 == 1:  # Mid lights
                intensity = mid_ratio
                base_color = [0, 255, 0]  # Green for mid
            else:  # Treble lights
                intensity = treble_ratio
                base_color = [0, 0, 255]  # Blue for treble
            
            # Apply intensity to color
            self.target_colors[light_name] = [
                int(base_color[0] * intensity),
                int(base_color[1] * intensity),
                int(base_color[2] * intensity)
            ]
    
    def _update_pulse_mode(self, palette: List, audio_features: Dict):
        """Pulse mode: All lights pulse together with beat."""
        beat_intensity = 1.0 if audio_features['beat_detected'] else 0.3
        
        # Cycle through palette colors slowly
        color_index = int((time.time() * 0.1) % len(palette))
        base_color = palette[color_index]
        
        for light_name in self.target_colors:
            self.target_colors[light_name] = [
                int(base_color[0] * beat_intensity),
                int(base_color[1] * beat_intensity),
                int(base_color[2] * beat_intensity)
            ]
    
    def _update_chase_mode(self, palette: List, audio_features: Dict):
        """Chase mode: Colors chase around the lights."""
        light_names = list(self.target_colors.keys())
        chase_speed = audio_features['tempo'] / 120.0  # Scale with tempo
        
        for i, light_name in enumerate(light_names):
            # Calculate position in chase
            position = (time.time() * chase_speed + i) % len(light_names)
            color_index = int(position) % len(palette)
            
            # Fade based on position within chase
            fade = 1.0 - abs((position % 1.0) - 0.5) * 2
            color = palette[color_index]
            
            self.target_colors[light_name] = [
                int(color[0] * fade),
                int(color[1] * fade),
                int(color[2] * fade)
            ]
    
    def _update_fade_mode(self, palette: List, audio_features: Dict):
        """Fade mode: Smooth color transitions across all lights."""
        # Cycle through colors smoothly
        self.color_cycle_position += self.color_cycle_speed
        
        for i, light_name in enumerate(self.target_colors.keys()):
            # Each light has a phase offset
            phase = self.color_cycle_position + (i * 0.2)
            
            # Interpolate between palette colors
            color_float = (phase % 1.0) * len(palette)
            color_index = int(color_float) % len(palette)
            next_index = (color_index + 1) % len(palette)
            blend = color_float % 1.0
            
            color1 = palette[color_index]
            color2 = palette[next_index]
            
            # Blend colors
            blended = [
                int(color1[0] * (1 - blend) + color2[0] * blend),
                int(color1[1] * (1 - blend) + color2[1] * blend),
                int(color1[2] * (1 - blend) + color2[2] * blend)
            ]
            
            self.target_colors[light_name] = blended
    
    def _update_strobe_mode(self, palette: List, audio_features: Dict):
        """Strobe mode: Synchronized strobing with beat."""
        if audio_features['beat_detected']:
            # Bright flash on beat
            color = random.choice(palette)
            for light_name in self.target_colors:
                self.target_colors[light_name] = color.copy()
        else:
            # Dark between beats
            for light_name in self.target_colors:
                self.target_colors[light_name] = [0, 0, 0]
    
    def _update_ping_pong_mode(self, palette: List, audio_features: Dict):
        """Ping pong mode: Sequential wave effect between lights with color cycling."""
        light_names = list(self.target_colors.keys())
        num_lights = len(light_names)
        
        if num_lights < 2:
            return
        
        # Update ping pong position based on beat or time
        if audio_features['beat_detected']:
            # Move faster on beats
            speed_multiplier = self.ping_pong_speed * 1.5
        else:
            speed_multiplier = self.ping_pong_speed * 0.5
        
        # Update position
        dt = 1.0 / 60.0  # Assuming 60 FPS
        self.ping_pong_position += self.ping_pong_direction * speed_multiplier * dt
        
        # Bounce at ends and change color
        if self.ping_pong_position >= num_lights - 1:
            self.ping_pong_position = num_lights - 1
            self.ping_pong_direction = -1
            self.ping_pong_color_index = (self.ping_pong_color_index + 1) % len(palette)
        elif self.ping_pong_position <= 0:
            self.ping_pong_position = 0
            self.ping_pong_direction = 1
            self.ping_pong_color_index = (self.ping_pong_color_index + 1) % len(palette)
        
        # Get current color with smooth transitions
        current_color = palette[self.ping_pong_color_index]
        next_color = palette[(self.ping_pong_color_index + 1) % len(palette)]
        
        # Calculate wave intensity for each light
        for i, light_name in enumerate(light_names):
            # Distance from ping pong position
            distance = abs(i - self.ping_pong_position)
            
            # Create a smooth wave effect
            wave_width = 2.0
            if distance <= wave_width:
                # Smooth falloff
                intensity = math.cos(distance * math.pi / (2 * wave_width)) ** 2
                
                # Blend colors based on beat intensity
                beat_blend = audio_features.get('beat_strength', 0.5) if audio_features['beat_detected'] else 0.2
                
                blended_color = [
                    int(current_color[0] * (1 - beat_blend) + next_color[0] * beat_blend),
                    int(current_color[1] * (1 - beat_blend) + next_color[1] * beat_blend),
                    int(current_color[2] * (1 - beat_blend) + next_color[2] * beat_blend)
                ]
                
                self.target_colors[light_name] = [
                    int(blended_color[0] * intensity),
                    int(blended_color[1] * intensity),
                    int(blended_color[2] * intensity)
                ]
            else:
                # Lights outside wave are dim
                self.target_colors[light_name] = [
                    int(current_color[0] * 0.1),
                    int(current_color[1] * 0.1),
                    int(current_color[2] * 0.1)
                ]
    
    def _update_flash_storm_mode(self, palette: List, audio_features: Dict):
        """Flash storm mode: Rapid color transitions with smooth fade effects."""
        current_time = time.time()
        
        # Update timers
        self.flash_random_timer += 1.0 / 60.0  # Assuming 60 FPS
        self.flash_color_timer += 1.0 / 60.0
        
        # Very frequent color changes for rapid transitions
        color_change_interval = 0.3  # Change every 0.3 seconds
        if self.flash_color_timer >= color_change_interval:
            self.flash_color_timer = 0
            # Change colors for random subset of lights
            light_names = list(self.target_colors.keys())
            num_to_change = random.randint(1, len(light_names))
            lights_to_change = random.sample(light_names, num_to_change)
            
            for light_name in lights_to_change:
                self.target_colors[light_name] = random.choice(palette).copy()
        
        # Enhanced beat response with smooth intensity boost
        if audio_features['beat_detected']:
            # Smooth intensity boost on beat (no strobing)
            beat_strength = audio_features.get('beat_strength', 1.0)
            intensity_boost = 1.0 + (beat_strength * 0.5)  # Max 1.5x intensity
            
            # Apply boost to all lights smoothly
            for light_name in self.target_colors:
                current_color = self.target_colors[light_name]
                boosted_color = [
                    min(255, int(current_color[0] * intensity_boost)),
                    min(255, int(current_color[1] * intensity_boost)),
                    min(255, int(current_color[2] * intensity_boost))
                ]
                self.target_colors[light_name] = boosted_color
            
            # Also trigger color changes on some lights for variety
            light_names = list(self.target_colors.keys())
            num_change = random.randint(1, max(1, len(light_names) // 2))
            change_lights = random.sample(light_names, num_change)
            
            for light_name in change_lights:
                self.target_colors[light_name] = random.choice(palette).copy()
        
        # Frequent random color transitions between beats
        elif self.flash_random_timer >= 0.15:  # Every 150ms
            self.flash_random_timer = 0
            
            # 40% chance of random color change
            if random.random() < 0.4:
                light_names = list(self.target_colors.keys())
                change_light = random.choice(light_names)
                new_color = random.choice(palette)
                
                # Smooth color transition, not a flash
                self.target_colors[change_light] = new_color.copy()
        
        # Dynamic intensity based on volume and tempo
        volume = audio_features.get('smoothed_volume', 0.5)
        tempo = audio_features.get('tempo', 120)
        
        # Base intensity varies with volume (never goes to zero)
        base_intensity = 0.4 + (volume * 0.6)  # Range: 0.4 to 1.0
        
        # Add subtle tempo-based variation
        tempo_factor = min(1.2, tempo / 120.0)  # Faster tempo = brighter
        final_intensity = base_intensity * tempo_factor
        
        # Apply smooth intensity scaling to all lights
        for light_name in self.target_colors:
            color = self.target_colors[light_name]
            self.target_colors[light_name] = [
                int(color[0] * final_intensity),
                int(color[1] * final_intensity),
                int(color[2] * final_intensity)
            ]
    
    def _apply_color_transitions(self):
        """Apply smooth transitions between current and target colors."""
        for light_name in self.current_colors:
            current = self.current_colors[light_name]
            target = self.target_colors[light_name]
            
            # Smooth transition
            for i in range(3):  # RGB
                diff = target[i] - current[i]
                current[i] += diff * self.transition_speed
                current[i] = max(0, min(255, int(current[i])))
    
    def _output_to_dmx(self):
        """Send current colors to DMX controller."""
        total_intensity = min(255, int((self.base_intensity + self.beat_intensity_boost) * 255))
        
        for light_name, color in self.current_colors.items():
            self.dmx_controller.set_light_rgb(
                light_name,
                color[0],
                color[1], 
                color[2],
                total_intensity
            )
    
    def set_palette(self, palette_name: str):
        """Manually set color palette."""
        if palette_name in self.color_palettes:
            self.current_palette = palette_name
            logger.info(f"Set color palette to: {palette_name}")
        else:
            logger.warning(f"Unknown palette: {palette_name}")
    
    def set_mode(self, mode: str):
        """Manually set effect mode."""
        valid_modes = ['auto', 'pulse', 'chase', 'strobe', 'fade', 'ping_pong', 'flash_storm']
        if mode in valid_modes:
            self.current_mode = mode
            self.mode_start_time = time.time()
            logger.info(f"Set effect mode to: {mode}")
        else:
            logger.warning(f"Unknown mode: {mode}")
    
    def get_status(self) -> Dict:
        """Get current effects engine status."""
        return {
            'current_mode': self.current_mode,
            'current_palette': self.current_palette,
            'base_intensity': self.base_intensity,
            'beat_intensity_boost': self.beat_intensity_boost,
            'transition_speed': self.transition_speed,
            'available_palettes': list(self.color_palettes.keys()),
            'available_modes': ['auto', 'pulse', 'chase', 'strobe', 'fade', 'ping_pong', 'flash_storm']
        }

