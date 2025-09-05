"""
Audio processing module for real-time beat detection and volume analysis.
Handles input from Sound Blaster USB dongle and extracts musical features.
"""

import os
import numpy as np
import librosa
import sounddevice as sd
import threading
import time
from collections import deque
from scipy import signal
import logging

# Configure environment for Pipewire compatibility
os.environ['PULSE_RUNTIME_PATH'] = '/run/user/' + str(os.getuid()) + '/pulse'
os.environ['PULSE_SERVER'] = 'unix:/run/user/' + str(os.getuid()) + '/pulse/native'

logger = logging.getLogger(__name__)

class AudioProcessor:
    def __init__(self, config):
        self.config = config['audio']
        self.processing_config = config['audio_processing']
        
        # Audio stream parameters
        self.sample_rate = self.config['sample_rate']
        self.buffer_size = self.config['buffer_size']
        self.input_channels = self.config['input_channels']
        
        # Beat detection parameters
        self.onset_threshold = self.processing_config['beat_detection']['onset_threshold']
        self.hop_length = self.processing_config['beat_detection']['hop_length']
        
        # Frequency band definitions
        self.freq_bands = self.processing_config['frequency_bands']
        
        # Volume processing
        self.volume_smoothing = self.processing_config['volume']['smoothing_factor']
        self.volume_gain = self.processing_config['volume']['gain']
        self.noise_floor = self.processing_config['volume']['noise_floor']
        
        # Audio buffers and state
        self.audio_buffer = deque(maxlen=self.sample_rate * 4)  # 4 seconds buffer
        self.current_volume = 0.0
        self.smoothed_volume = 0.0
        self.beat_detected = False
        self.beat_strength = 0.0
        self.frequency_powers = {'bass': 0.0, 'mid': 0.0, 'treble': 0.0}
        
        # Threading
        self.running = False
        self.audio_thread = None
        self.processing_thread = None
        
        # Beat detection state
        self.onset_times = deque(maxlen=100)
        self.last_beat_time = 0
        self.tempo = 120  # BPM
        
        # Initialize audio stream
        self.audio_stream = None
        self._setup_audio_device()
    
    def _setup_audio_device(self):
        """Find and configure audio device with Pipewire support."""
        try:
            devices = sd.query_devices()
            device_id = None
            
            logger.info("Scanning for audio devices...")
            logger.info(f"Looking for device: '{self.config['device_name']}' with {self.input_channels} input channels")
            
            # Log all available devices for debugging
            logger.info("Available audio devices:")
            for i, device in enumerate(devices):
                is_default_input = (i == sd.default.device[0])
                default_str = " (DEFAULT INPUT)" if is_default_input else ""
                logger.info(f"  Device {i}: {device['name']} (inputs: {device['max_input_channels']}){default_str}")
            
            # If device_name is "default", use the system default
            if self.config['device_name'] == 'default':
                device_id = None  # Use sounddevice default
                logger.info("Using system default audio device (Pipewire managed)")
            else:
                # Find specific device
                search_terms = [
                    self.config['device_name'].lower(),
                    'sound blaster',
                    'creative',
                    'blaster'
                ]
                
                for i, device in enumerate(devices):
                    device_name_lower = device['name'].lower()
                    
                    # Check if any search term matches and device has input channels
                    for search_term in search_terms:
                        if search_term in device_name_lower and device['max_input_channels'] >= self.input_channels:
                            device_id = i
                            logger.info(f"Found matching device: {device['name']} (ID: {i})")
                            break
                    
                    if device_id is not None:
                        break
                
                if device_id is None:
                    logger.warning(f"Specific device '{self.config['device_name']}' not found")
                    logger.info("Falling back to system default device")
                    device_id = None  # Use default
            
            self.device_id = device_id
            
            # Log final device selection
            if device_id is None:
                logger.info("Will use system default audio device")
            else:
                selected_device = devices[device_id]
                logger.info(f"Selected device: {selected_device['name']} (ID: {device_id})")
                
        except Exception as e:
            logger.error(f"Error setting up audio device: {e}")
            logger.info("Falling back to system default")
            self.device_id = None
    
    def _audio_callback(self, indata, frames, time, status):
        """Callback function for audio stream."""
        if status:
            # Only log overflow warnings occasionally to avoid spam
            if hasattr(status, 'input_overflow') and status.input_overflow:
                if not hasattr(self, '_last_overflow_warning'):
                    self._last_overflow_warning = 0
                current_time = time.time()
                if current_time - self._last_overflow_warning > 5:  # Only warn every 5 seconds
                    logger.warning(f"Audio input overflow detected - consider increasing buffer size")
                    self._last_overflow_warning = current_time
            elif status:
                logger.warning(f"Audio callback status: {status}")
        
        try:
            # Convert to mono if stereo, or use mono directly
            if self.input_channels == 2 and len(indata.shape) > 1 and indata.shape[1] >= 2:
                audio_data = np.mean(indata, axis=1)
            else:
                # Use first channel or mono channel
                audio_data = indata[:, 0] if len(indata.shape) > 1 and indata.shape[1] > 0 else indata.flatten()
            
            # Check if we're getting audio data
            audio_level = np.abs(audio_data).mean()
            if audio_level > 0.001:  # Only log if we have significant audio
                logger.debug(f"Audio level: {audio_level:.4f}")
            
            # Add to buffer (skip if processing is behind)
            if len(self.audio_buffer) < self.audio_buffer.maxlen * 0.9:  # Only fill to 90%
                self.audio_buffer.extend(audio_data)
        except Exception as e:
            logger.error(f"Error in audio callback: {e}")
    
    def start(self):
        """Start audio processing."""
        if self.running:
            return
        
        self.running = True
        
        # Start audio stream with Pipewire-compatible settings
        try:
            # First try with Pipewire-optimized settings
            self.audio_stream = sd.InputStream(
                device=self.device_id,
                channels=self.input_channels,
                samplerate=self.sample_rate,
                blocksize=self.buffer_size,
                callback=self._audio_callback,
                dtype=np.float32,
                latency='high'  # Use higher latency for Pipewire compatibility
            )
            logger.info("Created audio stream with Pipewire-optimized settings")
        except Exception as e:
            logger.warning(f"Failed to create optimized audio stream: {e}")
            logger.info("Trying with basic Pipewire settings...")
            try:
                # Fallback to basic Pipewire settings
                self.audio_stream = sd.InputStream(
                    device=self.device_id,
                    channels=self.input_channels,
                    samplerate=self.sample_rate,
                    blocksize=self.buffer_size,
                    callback=self._audio_callback,
                    dtype=np.float32
                )
                logger.info("Created audio stream with basic Pipewire settings")
            except Exception as e2:
                logger.warning(f"Failed with basic settings: {e2}")
                logger.info("Trying with minimal settings...")
                # Last resort - minimal settings
                self.audio_stream = sd.InputStream(
                    device=None,  # Use absolute default
                    channels=2,   # Force stereo
                    samplerate=44100,  # Force standard rate
                    callback=self._audio_callback
                )
                logger.info("Created audio stream with minimal default settings")
        
        self.audio_stream.start()
        
        # Start processing thread
        self.processing_thread = threading.Thread(target=self._processing_loop)
        self.processing_thread.start()
        
        logger.info("Audio processing started")
    
    def stop(self):
        """Stop audio processing."""
        self.running = False
        
        if self.audio_stream:
            self.audio_stream.stop()
            self.audio_stream.close()
        
        if self.processing_thread:
            self.processing_thread.join()
        
        logger.info("Audio processing stopped")
    
    def _processing_loop(self):
        """Main processing loop for audio analysis."""
        while self.running:
            try:
                if len(self.audio_buffer) < self.sample_rate:
                    time.sleep(0.01)
                    continue
                
                # Get recent audio data
                audio_data = np.array(list(self.audio_buffer)[-self.sample_rate:])
                
                # Process audio
                self._analyze_volume(audio_data)
                self._analyze_frequency_bands(audio_data)
                self._detect_beats(audio_data)
                
                time.sleep(1.0 / 60)  # 60 FPS processing
                
            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                time.sleep(0.1)
    
    def _analyze_volume(self, audio_data):
        """Analyze current volume level."""
        # Calculate RMS volume
        rms = np.sqrt(np.mean(audio_data ** 2))
        
        # Apply gain and noise floor
        volume = max(rms * self.volume_gain, self.noise_floor)
        
        # Smooth volume changes
        self.smoothed_volume = (self.volume_smoothing * self.smoothed_volume + 
                               (1 - self.volume_smoothing) * volume)
        
        self.current_volume = volume
        
        # Log volume levels periodically for debugging
        if not hasattr(self, '_last_volume_log'):
            self._last_volume_log = 0
        
        current_time = time.time()
        if current_time - self._last_volume_log > 3:  # Every 3 seconds
            logger.info(f"Audio levels - Raw RMS: {rms:.4f}, After gain ({self.volume_gain}x): {volume:.4f}, Smoothed: {self.smoothed_volume:.4f}")
            if rms < 0.0001:
                logger.warning("Very low audio levels detected - check audio input source and volume")
            self._last_volume_log = current_time
    
    def _analyze_frequency_bands(self, audio_data):
        """Analyze power in different frequency bands."""
        # Compute FFT
        fft = np.fft.fft(audio_data)
        freqs = np.fft.fftfreq(len(audio_data), 1/self.sample_rate)
        
        # Get magnitude spectrum
        magnitude = np.abs(fft)
        
        # Calculate power in each frequency band
        for band_name, (low_freq, high_freq) in self.freq_bands.items():
            # Find frequency indices
            freq_mask = (freqs >= low_freq) & (freqs <= high_freq)
            
            # Calculate average power in band
            if np.any(freq_mask):
                power = np.mean(magnitude[freq_mask])
                self.frequency_powers[band_name] = power
            else:
                self.frequency_powers[band_name] = 0.0
    
    def _detect_beats(self, audio_data):
        """Detect beats using onset detection."""
        try:
            # Use librosa for onset detection
            onset_frames = librosa.onset.onset_detect(
                y=audio_data,
                sr=self.sample_rate,
                hop_length=self.hop_length,
                threshold=self.onset_threshold,
                units='frames'
            )
            
            if len(onset_frames) > 0:
                # Convert frames to time
                onset_times = librosa.frames_to_time(
                    onset_frames, 
                    sr=self.sample_rate, 
                    hop_length=self.hop_length
                )
                
                # Check for recent beats
                current_time = time.time()
                recent_beats = onset_times[onset_times > (len(audio_data)/self.sample_rate - 0.1)]
                
                if len(recent_beats) > 0:
                    # Beat detected
                    self.beat_detected = True
                    self.last_beat_time = current_time
                    
                    # Calculate beat strength based on onset strength
                    onset_strength = librosa.onset.onset_strength(
                        y=audio_data,
                        sr=self.sample_rate,
                        hop_length=self.hop_length
                    )
                    
                    if len(onset_strength) > 0:
                        self.beat_strength = np.max(onset_strength[-10:])  # Recent strength
                    
                    logger.info(f"Beat detected! Strength: {self.beat_strength:.3f}, Total beats: {len(self.onset_times) + 1}")
                    
                    # Update tempo estimation
                    self.onset_times.append(current_time)
                    self._estimate_tempo()
                else:
                    self.beat_detected = False
            else:
                self.beat_detected = False
                
        except Exception as e:
            logger.error(f"Error in beat detection: {e}")
            self.beat_detected = False
    
    def _estimate_tempo(self):
        """Estimate current tempo from recent beats."""
        logger.info(f"Tempo estimation: {len(self.onset_times)} beats recorded")
        
        if len(self.onset_times) < 2:
            logger.info("Not enough beats for tempo estimation (need at least 2)")
            return
        
        # Calculate intervals between beats
        recent_onsets = list(self.onset_times)[-8:]  # Last 8 beats
        intervals = np.diff(recent_onsets)
        
        logger.info(f"Beat intervals: {intervals}")
        
        if len(intervals) > 0:
            # Filter out outliers
            median_interval = np.median(intervals)
            valid_intervals = intervals[
                (intervals > median_interval * 0.5) & 
                (intervals < median_interval * 2.0)
            ]
            
            logger.info(f"Valid intervals after filtering: {valid_intervals}")
            
            if len(valid_intervals) > 0:
                avg_interval = np.mean(valid_intervals)
                calculated_tempo = 60.0 / avg_interval  # Convert to BPM
                
                logger.info(f"Calculated tempo: {calculated_tempo:.1f} BPM (from avg interval: {avg_interval:.3f}s)")
                
                # Clamp to reasonable range
                self.tempo = np.clip(
                    calculated_tempo,
                    self.processing_config['beat_detection']['min_tempo'],
                    self.processing_config['beat_detection']['max_tempo']
                )
                
                logger.info(f"Final tempo (after clipping): {self.tempo:.1f} BPM")
    
    def get_audio_features(self):
        """Get current audio analysis features."""
        return {
            'volume': self.current_volume,
            'smoothed_volume': self.smoothed_volume,
            'beat_detected': self.beat_detected,
            'beat_strength': self.beat_strength,
            'tempo': self.tempo,
            'frequency_powers': self.frequency_powers.copy(),
            'time_since_beat': time.time() - self.last_beat_time
        }
    
    def is_running(self):
        """Check if audio processing is running."""
        return self.running

