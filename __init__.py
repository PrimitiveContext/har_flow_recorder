"""API Tool CLI - Browser Recording System

Enhanced browser recording with DOM interaction tracking and audio narration.
"""

__version__ = "1.0.0"
__author__ = "MVP Developer"

from .browser_recorder import EnhancedBrowserRecorder
from .audio_narrator import AudioNarrator
from .recording_manager import RecordingManager

__all__ = [
    "EnhancedBrowserRecorder",
    "AudioNarrator",
    "RecordingManager"
]