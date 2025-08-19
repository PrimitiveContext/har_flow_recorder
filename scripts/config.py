"""Configuration management for API Tool CLI"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).parent.parent
LOGS_DIR = BASE_DIR / "logs"
RECORDINGS_DIR = BASE_DIR / "recordings"

# Ensure directories exist
LOGS_DIR.mkdir(parents=True, exist_ok=True)
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

# API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Proxy Configuration
HTTP_PROXY = os.getenv("HTTP_PROXY", "")
HTTPS_PROXY = os.getenv("HTTPS_PROXY", "")

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = '%(asctime)s.%(msecs)03d | %(levelname)s | %(funcName)s | %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Audio Configuration
AUDIO_SAMPLE_RATE = int(os.getenv("AUDIO_SAMPLE_RATE", "16000"))
AUDIO_CHUNK_DURATION = int(os.getenv("AUDIO_CHUNK_DURATION", "30"))

# Browser Configuration
BROWSER_TIMEOUT = int(os.getenv("BROWSER_TIMEOUT", "30000"))
BROWSER_SLOW_MO = int(os.getenv("BROWSER_SLOW_MO", "0"))

# Recording Configuration
RECORDING_OUTPUT_DIR = Path(os.getenv("RECORDING_DIR", str(RECORDINGS_DIR)))
RECORDING_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def get_log_file(name: str) -> Path:
    """Get log file path for a specific component"""
    return LOGS_DIR / f"{name}.log"

def get_recording_dir(project: str, user: str = None) -> Path:
    """Get recording directory for a project/user"""
    if user:
        recording_dir = RECORDING_OUTPUT_DIR / project / user
    else:
        recording_dir = RECORDING_OUTPUT_DIR / project
    recording_dir.mkdir(parents=True, exist_ok=True)
    return recording_dir