#!/usr/bin/env python3
"""Test script to verify clean shutdown of browser recorder"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.browser_recorder import Phase1BrowserRecorder

# Force output to console
print("Starting test cleanup script...", flush=True)

# Setup minimal logging for test - output to both console and file
# Force output to console
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# Also write to file
file_handler = logging.FileHandler('test_cleanup.log')
file_handler.setLevel(logging.DEBUG)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[console_handler, file_handler],
    force=True  # Override any existing config
)
logger = logging.getLogger(__name__)

async def test_cleanup():
    """Test browser recorder cleanup with no errors"""
    recorder = None
    
    try:
        logger.info("Creating browser recorder...")
        recorder = Phase1BrowserRecorder(project="test_project")
        
        logger.info("Opening browser...")
        await recorder.open_browser(headless=True)
        
        logger.info("Starting recording...")
        result = await recorder.start_recording(
            user="test_user",
            description="Test cleanup",
            url="https://example.com"
        )
        
        if result["success"]:
            logger.info(f"Recording started: {result['session_id']}")
        
        # Wait a moment to let some events be captured
        await asyncio.sleep(2)
        
        logger.info("Stopping recording...")
        stop_result = await recorder.stop_recording()
        
        if stop_result["success"]:
            logger.info(f"Recording stopped successfully")
            logger.info(f"Session saved to: {stop_result['session_dir']}")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        
    finally:
        if recorder:
            logger.info("Running cleanup...")
            await recorder.cleanup()
            logger.info("Cleanup completed - check for error messages above")

if __name__ == "__main__":
    logger.info("Starting browser recorder cleanup test...")
    asyncio.run(test_cleanup())
    logger.info("Test completed - if no errors above, cleanup is working correctly!")