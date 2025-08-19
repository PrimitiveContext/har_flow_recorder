"""Audio recording and transcription for browser sessions"""

import logging
import time
import json
import threading
import queue
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import wave
import contextlib
import os
import sys

# ALSA suppressor context manager
@contextlib.contextmanager
def suppress_alsa():
    """Suppress ALL ALSA warnings during PyAudio operations"""
    # Set null audio environment before import
    os.environ['ALSA_CARD'] = 'null'
    os.environ['AUDIODEV'] = 'null'
    os.environ['ALSA_CARD'] = 'null'
    
    # Redirect stderr at OS level to completely silence ALSA
    devnull = os.open(os.devnull, os.O_WRONLY)
    old_stderr = os.dup(2)
    os.dup2(devnull, 2)
    os.close(devnull)
    
    try:
        yield
    finally:
        # Restore stderr
        os.dup2(old_stderr, 2)
        os.close(old_stderr)

# Import pyaudio with ALSA suppression
# Also set environment permanently to prevent any future ALSA issues
os.environ['ALSA_CARD'] = 'null'
os.environ['AUDIODEV'] = 'null'
os.environ['SDL_AUDIODRIVER'] = 'dummy'  # Also suppress SDL audio if used

with suppress_alsa():
    import pyaudio

from openai import OpenAI
import os
import numpy as np

# Comprehensive logging - FILE ONLY, no console spam
logging.basicConfig(
    level=logging.WARNING,  # Console gets warnings only
    format='%(message)s'
)

# Add detailed file logging
file_handler = logging.FileHandler('/tmp/recordings/audio_narrator.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s.%(msecs)03d | %(levelname)s | %(funcName)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))
logging.getLogger().addHandler(file_handler)
logger = logging.getLogger(__name__)

# MVP hardcoded values
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SIZE = 1024
AUDIO_FORMAT = pyaudio.paInt16
RECORDINGS_DIR = "/tmp/recordings"  # Default, will be overridden with project path

class AudioNarrator:
    def __init__(self, project: Optional[str] = None):
        start_time = time.time()
        logger.info(f"Starting AudioNarrator initialization for project: {project}")
        
        self.project = project
        self.pyaudio = None
        self.stream = None
        self.recording = False
        self.stop_recording_flag = threading.Event()  # Add threading event for clean shutdown
        self.audio_thread = None
        self.audio_queue = queue.Queue()
        self.audio_data = []
        self.recording_start = None
        self.session_dir = None  # Will be set when recording starts
        
        # Continuous transcription settings
        self.chunk_duration = 60  # Hardcoded 60 seconds for MVP
        self.continuous_transcription = False
        self.transcription_thread = None
        self.chunk_counter = 0
        self.events_file = None
        self.last_chunk_time = None
        
        # Initialize OpenAI client for Whisper API
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("No OPENAI_API_KEY found in environment")
            self.openai_client = None
        else:
            self.openai_client = OpenAI(api_key=api_key)
            logger.info("OpenAI client initialized for Whisper API")
        
        # Default recordings directory (will be overridden per session)
        Path(RECORDINGS_DIR).mkdir(parents=True, exist_ok=True)
        
        elapsed = (time.time() - start_time) * 1000
        logger.info(f"Completed initialization in {elapsed:.2f}ms")
    
    
    def _audio_recording_thread(self):
        """Background thread for audio recording"""
        logger.info("Audio recording thread started")
        
        try:
            # Initialize PyAudio with ALSA suppression
            with suppress_alsa():
                self.pyaudio = pyaudio.PyAudio()
            
            # MVP: Use default audio device, no fancy selection
            self.stream = self.pyaudio.open(
                format=AUDIO_FORMAT,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE
            )
            
            logger.debug("Audio stream opened")
            
            # Use smaller chunks and check stop flag more frequently
            while not self.stop_recording_flag.is_set():
                try:
                    # Non-blocking read with smaller chunks for faster response
                    if self.stream.get_read_available() >= CHUNK_SIZE:
                        data = self.stream.read(CHUNK_SIZE, exception_on_overflow=False)
                        self.audio_queue.put(data)
                    else:
                        # Small sleep to prevent CPU spinning
                        time.sleep(0.01)
                except Exception as e:
                    logger.warning(f"Audio read error (continuing): {e}")
                    if self.stop_recording_flag.is_set():
                        break
                    continue
                    
        except Exception as e:
            logger.error(f"Audio recording thread error: {e}")
        finally:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            if self.pyaudio:
                with suppress_alsa():
                    self.pyaudio.terminate()
            logger.info("Audio recording thread ended")
    
    def _continuous_transcription_thread(self):
        """Background thread for continuous transcription"""
        logger.info("Continuous transcription thread started")
        
        while not self.stop_recording_flag.is_set():
            try:
                # Wait for chunk duration or stop signal
                if self.stop_recording_flag.wait(timeout=self.chunk_duration):
                    break
                    
                # Time for a chunk transcription
                if len(self.audio_data) > 0:
                    self._process_audio_chunk()
                    
            except Exception as e:
                logger.error(f"Continuous transcription error: {e}")
                
        logger.info("Continuous transcription thread ended")
    
    def _process_audio_chunk(self):
        """Process and transcribe an audio chunk"""
        try:
            self.chunk_counter += 1
            chunk_start_time = self.last_chunk_time or 0
            chunk_end_time = time.time() - self.recording_start.timestamp()
            
            logger.info(f"Processing chunk {self.chunk_counter}: {chunk_start_time:.1f}s - {chunk_end_time:.1f}s")
            
            # Save current audio data as chunk
            chunk_data = self.audio_data.copy()
            chunk_path = self.session_dir / f"audio_chunk_{self.chunk_counter:03d}.wav"
            
            # Save chunk to file
            with wave.open(str(chunk_path), 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(2)  # 16-bit audio
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(b''.join(chunk_data))
            
            # Transcribe the chunk
            transcript_result = self.transcribe(str(chunk_path))
            
            # Write to events file
            if self.events_file:
                event = {
                    "type": "audio_transcript_chunk",
                    "data": {
                        "chunk_number": self.chunk_counter,
                        "audio_start_time": chunk_start_time,
                        "audio_end_time": chunk_end_time,
                        "transcription_timestamp": datetime.now().isoformat(),
                        "transcript": transcript_result.get("text", ""),
                        "segments": transcript_result.get("segments", [])
                    }
                }
                self.events_file.write(json.dumps(event) + "\n")
                self.events_file.flush()
            
            self.last_chunk_time = chunk_end_time
            logger.info(f"Chunk {self.chunk_counter} transcribed successfully")
            
        except Exception as e:
            logger.error(f"Failed to process audio chunk: {e}")
    
    def start_recording(self, session_id: str, continuous: bool = False, session_dir: Optional[str] = None) -> Dict[str, Any]:
        """Start audio recording with optional continuous transcription"""
        start_time = time.time()
        logger.info(f"Starting audio recording for session: {session_id} (continuous: {continuous})")
        
        try:
            if self.recording:
                logger.warning("Already recording")
                return {"success": False, "error": "Already recording"}
            
            self.recording = True
            self.stop_recording_flag.clear()  # Clear the stop flag
            self.recording_start = datetime.now()
            self.audio_data = []
            self.session_id = session_id
            self.continuous_transcription = continuous
            self.chunk_counter = 0
            self.last_chunk_time = None
            
            # Determine recording directory
            if session_dir:
                # Use the provided session directory from browser recorder
                self.session_dir = Path(session_dir)
            elif self.project:
                # Extract user from session_id (format: user_timestamp_hash)
                user = session_id.split('_')[0] if '_' in session_id else 'unknown'
                self.session_dir = Path(f"./{self.project}/recordings") / user / session_id
            else:
                # Fallback to tmp directory
                self.session_dir = Path(RECORDINGS_DIR) / session_id
            
            # Ensure directory exists
            self.session_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Audio session directory: {self.session_dir}")
            
            # Open events file if continuous transcription
            if continuous:
                events_path = self.session_dir / "audio_events.ndjson"
                self.events_file = open(events_path, 'w')
                logger.info(f"Events file opened: {events_path}")
            
            # Start recording thread
            self.audio_thread = threading.Thread(target=self._audio_recording_thread)
            self.audio_thread.daemon = True
            self.audio_thread.start()
            
            # Process audio queue in main thread
            def process_queue():
                while not self.stop_recording_flag.is_set():
                    try:
                        data = self.audio_queue.get(timeout=0.1)
                        self.audio_data.append(data)
                    except queue.Empty:
                        continue
            
            # Start queue processor in background
            self.queue_processor = threading.Thread(target=process_queue)
            self.queue_processor.daemon = True
            self.queue_processor.start()
            
            # Start continuous transcription if enabled
            if continuous:
                self.transcription_thread = threading.Thread(target=self._continuous_transcription_thread)
                self.transcription_thread.daemon = True
                self.transcription_thread.start()
                logger.info("Continuous transcription started")
            
            elapsed = (time.time() - start_time) * 1000
            logger.info(f"Audio recording started in {elapsed:.2f}ms")
            
            return {
                "success": True,
                "start_time": self.recording_start.isoformat(),
                "continuous": continuous
            }
            
        except Exception as e:
            logger.error(f"Failed to start audio recording: {e}")
            self.recording = False
            return {"success": False, "error": str(e)}
    
    def stop_recording(self) -> Dict[str, Any]:
        """Stop audio recording and save"""
        start_time = time.time()
        logger.info("Stopping audio recording")
        
        try:
            if not self.recording:
                logger.warning("Not recording")
                return {"success": False, "error": "Not recording"}
            
            self.recording = False
            self.stop_recording_flag.set()  # Signal threads to stop
            recording_end = datetime.now()
            duration = (recording_end - self.recording_start).total_seconds()
            
            # Wait for threads to finish with timeout
            if self.audio_thread:
                self.audio_thread.join(timeout=2.0)
                if self.audio_thread.is_alive():
                    logger.warning("Audio thread did not stop in time, forcing termination")
            if hasattr(self, 'queue_processor'):
                self.queue_processor.join(timeout=1.0)
                if self.queue_processor.is_alive():
                    logger.warning("Queue processor did not stop in time")
            if self.transcription_thread:
                self.transcription_thread.join(timeout=2.0)
                if self.transcription_thread.is_alive():
                    logger.warning("Transcription thread did not stop in time")
            
            # Process remaining queue items
            while not self.audio_queue.empty():
                try:
                    data = self.audio_queue.get_nowait()
                    self.audio_data.append(data)
                except queue.Empty:
                    break
            
            # Close events file if continuous transcription was active
            if self.events_file:
                # Process final chunk if there's remaining audio
                if self.continuous_transcription and len(self.audio_data) > 0:
                    self._process_audio_chunk()
                self.events_file.close()
                self.events_file = None
                logger.info("Events file closed")
            
            logger.info(f"Captured {len(self.audio_data)} audio chunks")
            
            # Save audio file to session directory
            audio_path = self.session_dir / "audio.wav"
            self._save_audio(audio_path)
            
            elapsed = (time.time() - start_time) * 1000
            logger.info(f"Audio recording stopped in {elapsed:.2f}ms")
            
            return {
                "success": True,
                "audio_path": str(audio_path),
                "duration": duration,
                "chunks": len(self.audio_data)
            }
            
        except Exception as e:
            logger.error(f"Failed to stop audio recording: {e}")
            return {"success": False, "error": str(e)}
    
    def _save_audio(self, audio_path: Path):
        """Save recorded audio to WAV file"""
        logger.info(f"Saving audio to {audio_path}")
        
        try:
            with wave.open(str(audio_path), 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(self.pyaudio.get_sample_size(AUDIO_FORMAT) if self.pyaudio else 2)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(b''.join(self.audio_data))
            
            logger.debug(f"Audio saved: {audio_path.stat().st_size} bytes")
            
        except Exception as e:
            logger.error(f"Failed to save audio: {e}")
            raise
    
    def transcribe(self, audio_path: str) -> Dict[str, Any]:
        """Transcribe audio using OpenAI Whisper API"""
        start_time = time.time()
        logger.info(f"Transcribing audio using OpenAI Whisper API: {audio_path}")
        
        if not self.openai_client:
            logger.error("OpenAI API key not configured")
            return {
                "success": False,
                "error": "OpenAI API key not configured",
                "text": "[Transcription unavailable - No API key]"
            }
        
        try:
            # Open audio file
            with open(audio_path, 'rb') as audio_file:
                logger.debug("Calling OpenAI Whisper API")
                # Call OpenAI Whisper API
                transcript = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",  # OpenAI's Whisper model
                    file=audio_file,
                    response_format="verbose_json",  # Get timestamps
                    language="en"  # English for technical terms
                )
            
            # Parse response - transcript is a Transcription object
            segments = []
            
            # Check if we have segments (verbose_json format provides them)
            if hasattr(transcript, 'segments') and transcript.segments:
                for segment in transcript.segments:
                    # Access attributes directly, not via subscript
                    segments.append({
                        "start": getattr(segment, 'start', 0),
                        "end": getattr(segment, 'end', 0),
                        "text": getattr(segment, 'text', '')
                    })
                logger.debug(f"Parsed {len(segments)} segments from API response")
            
            # Get the full text
            full_text = transcript.text if hasattr(transcript, 'text') else str(transcript)
            
            elapsed = (time.time() - start_time) * 1000
            logger.info(f"Transcription successful: {len(segments)} segments in {elapsed:.2f}ms")
            logger.debug(f"Transcribed text: {full_text[:100]}...")  # Log first 100 chars
            
            # Get duration if available
            duration = getattr(transcript, 'duration', None)
            
            return {
                "success": True,
                "text": full_text,
                "segments": segments,
                "duration": duration,
                "language": "en"
            }
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "text": "[Transcription failed]"
            }
    
    def sync_with_timeline(self, transcript: Dict[str, Any], har_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Sync transcription with HAR timeline"""
        logger.info("Syncing transcript with HAR timeline")
        
        try:
            if not transcript.get("segments"):
                logger.warning("No transcript segments to sync")
                return []
            
            # Extract HAR entries with timestamps
            har_entries = []
            if har_data and "log" in har_data and "entries" in har_data["log"]:
                for entry in har_data["log"]["entries"]:
                    har_entries.append({
                        "timestamp": entry.get("startedDateTime"),
                        "url": entry.get("request", {}).get("url"),
                        "method": entry.get("request", {}).get("method"),
                        "status": entry.get("response", {}).get("status")
                    })
            
            # Create timeline combining audio and HAR events
            timeline = []
            
            # Add transcript segments
            for segment in transcript["segments"]:
                timeline.append({
                    "type": "narration",
                    "timestamp": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"]
                })
            
            # Sort timeline by timestamp
            timeline.sort(key=lambda x: x.get("timestamp", 0))
            
            logger.info(f"Created timeline with {len(timeline)} events")
            return timeline
            
        except Exception as e:
            logger.error(f"Failed to sync timeline: {e}")
            return []
    
    def cleanup(self):
        """Cleanup audio resources"""
        logger.info("Cleaning up audio resources")
        
        self.recording = False
        self.stop_recording_flag.set()  # Signal any running threads to stop
        
        # Give threads a moment to finish
        if self.audio_thread and self.audio_thread.is_alive():
            self.audio_thread.join(timeout=0.5)
        
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except:
                pass
        
        if self.pyaudio:
            try:
                with suppress_alsa():
                    self.pyaudio.terminate()
            except:
                pass
        
        logger.info("Audio cleanup completed")