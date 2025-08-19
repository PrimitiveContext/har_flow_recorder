#!/bin/bash

# API Tool CLI Runner Script

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}API Tool CLI Phase 1 - LOSSLESS Browser Recording System${NC}"
echo "========================================"

# Create logs directory if it doesn't exist
mkdir -p logs

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import playwright" 2>/dev/null; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -r requirements.txt
    
    # Install playwright browsers
    echo -e "${YELLOW}Installing Chromium browser...${NC}"
    playwright install chromium
fi

# Check command
if [ "$1" = "menu" ]; then
    echo -e "${GREEN}Starting interactive menu...${NC}"
    python -m scripts.cli menu
elif [ "$1" = "record" ]; then
    shift  # Remove 'record' from arguments
    echo -e "${GREEN}Starting recording session...${NC}"
    python -m scripts.cli record "$@"
elif [ "$1" = "test" ]; then
    echo -e "${GREEN}Running component tests...${NC}"
    python -m scripts.cli test
elif [ "$1" = "help" ] || [ -z "$1" ]; then
    echo ""
    echo "Usage: ./run.sh [command] [options]"
    echo ""
    echo "Commands:"
    echo "  menu     - Show interactive menu with project selection"
    echo "  record   - Start a new recording session or list project recordings"
    echo "  test     - Test browser and audio components"
    echo "  help     - Show this help message"
    echo ""
    echo "Recording options:"
    echo "  --project PROJECT     - Project name (required)"
    echo "  --user USER          - User identifier (required for recording)"
    echo "  --description DESC   - Recording description (required with --user)"
    echo "  --audio/--no-audio  - Enable/disable audio narration"
    echo "  --url URL           - Initial URL to navigate to"
    echo ""
    echo "Examples:"
    echo "  ./run.sh menu"
    echo "  ./run.sh record --project myapp --user john --description 'Login flow'"
    echo "  ./run.sh record --project myapp  # List recordings for project"
    echo "  ./run.sh test"
else
    echo -e "${RED}Unknown command: $1${NC}"
    echo "Run './run.sh help' for usage information"
fi