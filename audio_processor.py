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

# Configure environment for Pipewire compatibility - force ALSA backend
os.environ['SD_ENABLE_PULSE'] = '0'  # Disable PulseAudio backend
os.environ['SDL_AUDIODRIVER'] = 'alsa'  # Force ALSA
# Remove any PulseAudio environment variables that might interfere
for env_var in ['PULSE_RUNTIME_PATH', 'PULSE_SERVER']:
    if env_var in os.environ:
        del os.environ[env_var]

logger = logging.getLogger(__name__)

class AudioProcessor:
    def __init__(self, config):
        # Force sounddevice to use ALSA backend
        try:
            sd.default.hostapi = 'ALSA'
            logger.info("Forced sounddevice to use ALSA backend")
        except Exception as e:
            logger.warning(f"Could not force ALSA backend: {e}")
        
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

    def _list_candidate_devices(self, devices, configured_device_name):
        """Return a prioritized list of device indices to try opening.

        Priority order:
        1) Devices whose names match Sound Blaster/Creative/S3 and have inputs
        2) Device explicitly matching configured name substring (if not default)
        3) Device named 'default' (PortAudio/ALSA default)
        4) Any other device with input channels
        """
        candidate_indices = []

        lower_name = (configured_device_name or '').lower()
        preferred_substrings = ['sound blaster', 'creative', 'blaster', 's3']

        # 1) Prefer Sound Blaster style names
        for i, device in enumerate(devices):
            if device['max_input_channels'] <= 0:
                continue
            device_name_lower = device['name'].lower()
            if any(term in device_name_lower for term in preferred_substrings):
                candidate_indices.append(i)

        # 2) If a specific name was provided (and not 'default'), add matches
        if lower_name and lower_name != 'default' and not lower_name.startswith('hw:'):
            for i, device in enumerate(devices):
                if device['max_input_channels'] <= 0:
                    continue
                if lower_name in device['name'].lower() and i not in candidate_indices:
                    candidate_indices.append(i)

        # 3) Add a device literally named 'default' if present
        for i, device in enumerate(devices):
            if device['max_input_channels'] <= 0:
                continue
            if device['name'].strip().lower() == 'default' and i not in candidate_indices:
                candidate_indices.append(i)

        # 4) Add all remaining input-capable devices
        for i, device in enumerate(devices):
            if device['max_input_channels'] <= 0:
                continue
            if i not in candidate_indices:
                candidate_indices.append(i)

        return candidate_indices

    def _probe_working_device(self, devices, candidate_indices):
        """Try opening each candidate device briefly; return first working index or None."""
        for device_index in candidate_indices:
            device_info = devices[device_index]
            input_channels_supported = device_info['max_input_channels']
            channels_to_use = min(max(1, self.input_channels), input_channels_supported)

            logger.info(
                f"Probing device {device_index}: '{device_info['name']}' (inputs: {input_channels_supported}), using {channels_to_use} channels"
            )

            try:
                sd.check_input_settings(
                    device=device_index,
                    channels=channels_to_use,
                    samplerate=self.sample_rate
                )
            except Exception as e:
                logger.warning(f"check_input_settings failed for device {device_index}: {e}")
                continue

            try:
                with sd.InputStream(
                    device=device_index,
                    channels=channels_to_use,
                    samplerate=self.sample_rate,
                    blocksize=min(self.buffer_size, 1024),
                    dtype=np.float32,
                    latency='high'
                ) as _:
                    logger.info(f"Successfully opened device {device_index}: '{device_info['name']}'")
                    # Update input channels to what we actually can use
                    self.input_channels = channels_to_use
                    return device_index
            except Exception as e:
                logger.warning(f"Failed to open device {device_index} ('{device_info['name']}'): {e}")

        return None
    
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
            
            # Build candidate list and probe for a working device
            configured_device_name = self.config.get('device_name', 'default')
            candidate_indices = self._list_candidate_devices(devices, configured_device_name)
            logger.info(f"Candidate devices to probe (in order): {candidate_indices}")

            working_device = self._probe_working_device(devices, candidate_indices)

            if working_device is None:
                logger.warning("No input device could be opened. Falling back to system default (None)")
                device_id = None
            else:
                device_id = working_device
            
            self.device_id = device_id
            
            # Log final device selection
            if device_id is None:
                logger.info("Will use system default audio device")
            else:
                selected_device = devices[device_id]
                logger.info(f"Selected working device: {selected_device['name']} (ID: {device_id})")
                
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
        
        # Start audio stream using device ID
        try:
            # Try with detected device ID
            self.audio_stream = sd.InputStream(
                device=self.device_id,
                channels=self.input_channels,
                samplerate=self.sample_rate,
                blocksize=self.buffer_size,
                callback=self._audio_callback,
                dtype=np.float32,
                latency='high'
            )
            device_name = "default" if self.device_id is None else f"device {self.device_id}"
            logger.info(f"Created audio stream with {device_name}")
        except Exception as e:
            logger.warning(f"Failed to create audio stream with device {self.device_id}: {e}")
            logger.info("Trying with system default...")
            try:
                # Fallback to system default
                self.audio_stream = sd.InputStream(
                    device=None,
                    channels=2,
                    samplerate=44100,
                    blocksize=2048,
                    callback=self._audio_callback,
                    dtype=np.float32
                )
                logger.info("Created audio stream with system default")
            except Exception as e2:
                logger.error(f"Failed to create any audio stream: {e2}")
                raise
        
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

