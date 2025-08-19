#!/bin/bash

# Development runner script with enhanced error handling

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     API Tool CLI - Browser Recording & Security       ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to check command existence
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python installation
if ! command_exists python3; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo -e "${RED}Error: Python $REQUIRED_VERSION or higher is required (found $PYTHON_VERSION)${NC}"
    exit 1
fi

# Create logs and recordings directories
mkdir -p logs recordings

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to create virtual environment${NC}"
        exit 1
    fi
fi

# Activate virtual environment
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to activate virtual environment${NC}"
    exit 1
fi

# Check if dependencies are installed
if ! python -c "import playwright" 2>/dev/null; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install --upgrade pip
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to install dependencies${NC}"
        exit 1
    fi
    
    # Install playwright browsers
    echo -e "${YELLOW}Installing Chromium browser...${NC}"
    playwright install chromium
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to install Chromium${NC}"
        echo "You may need to install system dependencies:"
        echo "  Ubuntu/Debian: playwright install-deps"
        exit 1
    fi
fi

# Check for .env file
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    echo -e "${YELLOW}Note: No .env file found. Copy .env.example to .env and add your API keys.${NC}"
fi

# Function to show help
show_help() {
    echo -e "${BLUE}Usage:${NC} ./run_dev.sh [command] [options]"
    echo ""
    echo -e "${BLUE}Commands:${NC}"
    echo "  menu     - Show interactive menu with project selection"
    echo "  record   - Start a new recording session or list project recordings"
    echo "  test     - Test browser and audio components"
    echo "  install  - Install/reinstall dependencies"
    echo "  clean    - Clean logs and temporary files"
    echo "  help     - Show this help message"
    echo ""
    echo -e "${BLUE}Recording options:${NC}"
    echo "  --project PROJECT     - Project name (required)"
    echo "  --user USER          - User identifier (required for recording)"
    echo "  --description DESC   - Recording description (required with --user)"
    echo "  --audio/--no-audio  - Enable/disable audio narration"
    echo "  --url URL           - Initial URL to navigate to"
    echo "  --proxy URL         - Proxy server URL (e.g., http://127.0.0.1:8080)"
    echo "  --headless          - Run browser in headless mode"
    echo ""
    echo -e "${BLUE}Examples:${NC}"
    echo "  ./run_dev.sh menu"
    echo "  ./run_dev.sh record --project myapp --user john --description 'Login test'"
    echo "  ./run_dev.sh record --project myapp  # List recordings"
    echo "  ./run_dev.sh test"
    echo "  ./run_dev.sh clean"
}

# Parse command
case "$1" in
    menu)
        echo -e "${GREEN}Starting interactive menu...${NC}"
        python -m scripts.cli menu
        ;;
    record)
        shift
        echo -e "${GREEN}Starting recording session...${NC}"
        python -m scripts.cli record "$@"
        ;;
    test)
        echo -e "${GREEN}Running component tests...${NC}"
        python -m scripts.cli test
        ;;
    install)
        echo -e "${YELLOW}Reinstalling dependencies...${NC}"
        pip install --upgrade pip
        pip install -r requirements.txt --force-reinstall
        playwright install chromium --force
        echo -e "${GREEN}Dependencies reinstalled successfully${NC}"
        ;;
    clean)
        echo -e "${YELLOW}Cleaning temporary files...${NC}"
        find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
        find . -type f -name "*.pyc" -delete 2>/dev/null
        find . -type f -name "*.pyo" -delete 2>/dev/null
        if [ -d "logs" ]; then
            echo -e "${YELLOW}Clear log files? (y/N)${NC}"
            read -r response
            if [[ "$response" =~ ^[Yy]$ ]]; then
                rm -f logs/*.log
                echo -e "${GREEN}Log files cleared${NC}"
            fi
        fi
        echo -e "${GREEN}Cleanup complete${NC}"
        ;;
    help|--help|-h|"")
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac