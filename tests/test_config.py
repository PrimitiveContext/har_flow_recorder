"""Tests for configuration module"""

import os
import pytest
from pathlib import Path
from scripts.config import (
    BASE_DIR, LOGS_DIR, RECORDINGS_DIR,
    get_log_file, get_recording_dir
)


class TestConfig:
    """Test configuration settings"""
    
    def test_base_directories_exist(self):
        """Test that base directories are created"""
        assert LOGS_DIR.exists()
        assert RECORDINGS_DIR.exists()
    
    def test_get_log_file(self):
        """Test log file path generation"""
        log_file = get_log_file("test_component")
        assert log_file.parent == LOGS_DIR
        assert log_file.name == "test_component.log"
    
    def test_get_recording_dir_project_only(self):
        """Test recording directory for project only"""
        recording_dir = get_recording_dir("test_project")
        assert recording_dir.parent == RECORDINGS_DIR
        assert recording_dir.name == "test_project"
        assert recording_dir.exists()
    
    def test_get_recording_dir_with_user(self):
        """Test recording directory with user"""
        recording_dir = get_recording_dir("test_project", "test_user")
        assert recording_dir.parent.parent == RECORDINGS_DIR
        assert recording_dir.parent.name == "test_project"
        assert recording_dir.name == "test_user"
        assert recording_dir.exists()
    
    def test_environment_variables(self):
        """Test environment variable loading"""
        # These should work with or without .env file
        from scripts.config import LOG_LEVEL, AUDIO_SAMPLE_RATE
        assert LOG_LEVEL in ["DEBUG", "INFO", "WARNING", "ERROR"]
        assert isinstance(AUDIO_SAMPLE_RATE, int)
        assert AUDIO_SAMPLE_RATE > 0