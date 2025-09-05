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

# Configure environment for better audio compatibility on Raspberry Pi
try:
    # Try to disable PulseAudio backend for sounddevice
    os.environ['SD_ENABLE_PULSE'] = '0'
    # Remove any PulseAudio environment variables that might interfere
    for env_var in ['PULSE_RUNTIME_PATH', 'PULSE_SERVER']:
        if env_var in os.environ:
            del os.environ[env_var]
except Exception:
    pass  # Ignore any environment setup errors

logger = logging.getLogger(__name__)

class AudioProcessor:
    def __init__(self, config):
        # Log available host APIs for debugging
        try:
            hostapis = sd.query_hostapis()
            logger.info("Available host APIs:")
            for i, api in enumerate(hostapis):
                logger.info(f"  {i}: {api['name']}")
        except Exception as e:
            logger.warning(f"Could not query host APIs: {e}")
        
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
    
    def _probe_audio_device(self, device_id, device_info, test_channels):
        """Test if a specific audio device actually works."""
        try:
            # Quick compatibility check first
            sd.check_input_settings(
                device=device_id,
                channels=test_channels,
                samplerate=self.sample_rate
            )
            
            # Actually try to record for 0.1 seconds with minimal settings
            import numpy as np
            test_data = sd.rec(
                int(0.1 * self.sample_rate),
                samplerate=self.sample_rate,
                channels=test_channels,
                device=device_id,
                dtype=np.float32,
                blocking=True  # Ensure we wait for completion
            )
            
            # Check if we got actual audio data
            if test_data is not None and len(test_data) > 0:
                max_level = np.max(np.abs(test_data))
                logger.info(f"  Test recording: max level {max_level:.4f}")
                return True, test_channels
            else:
                logger.warning("  Test recording returned no data")
                return False, 0
            
        except Exception as e:
            logger.warning(f"  Device test failed: {e}")
            return False, 0

    def _run_alsa_diagnostics(self):
        """Run ALSA diagnostics to compare with sounddevice."""
        try:
            import subprocess
            logger.info("=== ALSA HARDWARE DIAGNOSTICS ===")
            
            # Get ALSA capture devices
            result = subprocess.run(['arecord', '-l'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                logger.info("ALSA capture devices:")
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        logger.info(f"  {line}")
            else:
                logger.warning("Could not get ALSA devices")
                
        except Exception as e:
            logger.warning(f"ALSA diagnostics failed: {e}")

    def _setup_audio_device(self):
        """Setup audio device with comprehensive diagnostics."""
        try:
            logger.info("=== AUDIO SYSTEM DIAGNOSTICS ===")
            
            # Show host APIs
            hostapis = sd.query_hostapis()
            logger.info("Available host APIs:")
            for i, api in enumerate(hostapis):
                default_in = api.get('default_input_device', -1)
                default_out = api.get('default_output_device', -1)
                logger.info(f"  {i}: {api['name']} (default in: {default_in}, out: {default_out})")
            
            # Show ALSA vs sounddevice comparison
            self._run_alsa_diagnostics()
            
            # Get all sounddevice devices
            devices = sd.query_devices()
            logger.info("=== SOUNDDEVICE DEVICE ANALYSIS ===")
            
            sound_blaster_devices = []
            input_devices = []
            
            for i, device in enumerate(devices):
                inputs = device['max_input_channels']
                outputs = device['max_output_channels']
                hostapi = device['hostapi']
                name = device['name']
                
                # Check if it's a Sound Blaster
                name_lower = name.lower()
                is_sound_blaster = any(term in name_lower for term in 
                                     ['sound blaster', 'creative', 'blaster', 's3'])
                
                logger.info(f"Device {i}: {name}")
                logger.info(f"  Inputs: {inputs}, Outputs: {outputs}, Host API: {hostapi}")
                logger.info(f"  Sample Rate: {device['default_samplerate']}")
                
                if is_sound_blaster:
                    sound_blaster_devices.append((i, device))
                    logger.info(f"  *** SOUND BLASTER DETECTED ***")
                
                if inputs > 0:
                    input_devices.append((i, device))
                    logger.info(f"  *** HAS INPUT CHANNELS ***")
                
                logger.info("")
            
            # Report findings
            logger.info(f"Found {len(sound_blaster_devices)} Sound Blaster device(s)")
            logger.info(f"Found {len(input_devices)} input-capable device(s)")
            
            # Strategy 1: Use configured device ID if specified
            device_name = self.config['device_name']
            if isinstance(device_name, (int, str)) and str(device_name).isdigit():
                device_id = int(device_name)
                logger.info(f"=== TESTING CONFIGURED DEVICE {device_id} ===")
                
                if device_id < len(devices):
                    device_info = devices[device_id]
                    logger.info(f"Device {device_id}: {device_info['name']}")
                    logger.info(f"  Max inputs: {device_info['max_input_channels']}")
                    
                    if device_info['max_input_channels'] > 0:
                        # Try stereo first, then mono
                        for test_channels in [2, 1]:
                            if test_channels <= device_info['max_input_channels']:
                                logger.info(f"Testing {test_channels} channel(s)...")
                                success, working_channels = self._probe_audio_device(device_id, device_info, test_channels)
                                if success:
                                    self.device_id = device_id
                                    self.input_channels = working_channels
                                    logger.info(f"✓ SUCCESS: Using configured device {device_id} with {working_channels} channels")
                                    return
                    else:
                        logger.warning(f"Configured device {device_id} has no input channels!")
                else:
                    logger.warning(f"Configured device ID {device_id} doesn't exist (max: {len(devices)-1})")
            
            # Strategy 2: Try all Sound Blaster devices
            logger.info("=== TESTING SOUND BLASTER DEVICES ===")
            for device_id, device_info in sound_blaster_devices:
                logger.info(f"Testing Sound Blaster device {device_id}: {device_info['name']}")
                
                if device_info['max_input_channels'] > 0:
                    for test_channels in [2, 1]:
                        if test_channels <= device_info['max_input_channels']:
                            success, working_channels = self._probe_audio_device(device_id, device_info, test_channels)
                            if success:
                                self.device_id = device_id
                                self.input_channels = working_channels
                                logger.info(f"✓ SUCCESS: Using Sound Blaster device {device_id} with {working_channels} channels")
                                return
                else:
                    logger.warning(f"Sound Blaster device {device_id} has no input channels!")
            
            # Strategy 3: Try any input device
            logger.info("=== TESTING ALL INPUT DEVICES ===")
            for device_id, device_info in input_devices:
                # Skip if already tested as Sound Blaster
                if (device_id, device_info) in sound_blaster_devices:
                    continue
                    
                logger.info(f"Testing input device {device_id}: {device_info['name']}")
                success, working_channels = self._probe_audio_device(device_id, device_info, min(2, device_info['max_input_channels']))
                if success:
                    self.device_id = device_id
                    self.input_channels = working_channels
                    logger.info(f"✓ SUCCESS: Using input device {device_id} with {working_channels} channels")
                    return
            
            # Strategy 4: System default
            logger.info("=== TESTING SYSTEM DEFAULT ===")
            for test_channels in [2, 1]:
                try:
                    import numpy as np
                    logger.info(f"Testing default device with {test_channels} channels...")
                    test_data = sd.rec(
                        int(0.1 * self.sample_rate),
                        samplerate=self.sample_rate,
                        channels=test_channels,
                        dtype=np.float32,
                        blocking=True
                    )
                    
                    if test_data is not None and len(test_data) > 0:
                        self.device_id = None
                        self.input_channels = test_channels
                        logger.info(f"✓ SUCCESS: Using system default with {test_channels} channels")
                        return
                        
                except Exception as e:
                    logger.warning(f"Default device test failed with {test_channels} channels: {e}")
            
            # If we get here, nothing worked
            logger.error("❌ NO WORKING AUDIO INPUT FOUND")
            logger.error("Please check:")
            logger.error("  1. Sound Blaster is plugged in and detected by ALSA")
            logger.error("  2. No other applications are using the audio device")
            logger.error("  3. User has permissions to access audio devices")
            
            # Final fallback to prevent crashes
            self.device_id = None
            self.input_channels = 2
                
        except Exception as e:
            logger.error(f"Audio device setup failed: {e}")
            self.device_id = None
            self.input_channels = 2
    
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
    
    def get_status(self):
        """Get current audio processing status including device info."""
        status = {
            'status': 'running' if self.running else 'stopped',
            'volume': self.current_volume if self.running else 0.0,
            'tempo': self.current_tempo if self.running else 0,
            'beat_detected': self.beat_detected if self.running else False
        }
        
        if self.running:
            status['last_beat'] = self.last_beat_time
            
        # Add device information
        try:
            if self.device_id is None:
                status['device'] = 'System Default'
            else:
                devices = sd.query_devices()
                device_info = devices[self.device_id]
                status['device'] = f"{device_info['name']} (ID: {self.device_id})"
            
            status['channels'] = self.input_channels
            status['sample_rate'] = self.sample_rate
            
        except Exception:
            status['device'] = 'Unknown'
            status['channels'] = self.input_channels
            status['sample_rate'] = self.sample_rate
            
        return status
    
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

