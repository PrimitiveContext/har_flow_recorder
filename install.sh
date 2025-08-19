#!/bin/bash

# API Tool CLI - Quick Installation Script

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     API Tool CLI - Installation Script                ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

# Function to check command
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

OS=$(detect_os)
echo -e "${BLUE}Detected OS:${NC} $OS"
echo ""

# Check Python
echo -e "${YELLOW}Checking Python installation...${NC}"
if ! command_exists python3; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    echo "Please install Python 3.8 or higher from https://www.python.org"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"

# Install system dependencies
echo ""
echo -e "${YELLOW}Installing system dependencies...${NC}"

case $OS in
    linux)
        if command_exists apt-get; then
            echo "Installing Linux dependencies..."
            sudo apt-get update
            sudo apt-get install -y portaudio19-dev python3-pip python3-venv
        elif command_exists yum; then
            echo "Installing Linux dependencies..."
            sudo yum install -y portaudio-devel python3-pip
        else
            echo -e "${YELLOW}Warning: Could not detect package manager${NC}"
            echo "Please manually install: portaudio development files"
        fi
        ;;
    macos)
        if command_exists brew; then
            echo "Installing macOS dependencies..."
            brew install portaudio
        else
            echo -e "${YELLOW}Warning: Homebrew not found${NC}"
            echo "Install Homebrew from https://brew.sh or manually install portaudio"
        fi
        ;;
    windows)
        echo -e "${YELLOW}Windows detected${NC}"
        echo "Please ensure you have:"
        echo "  1. Python 3.8+ installed"
        echo "  2. Visual C++ Build Tools (for pyaudio)"
        echo ""
        echo "You may need to install pyaudio manually:"
        echo "  pip install pipwin"
        echo "  pipwin install pyaudio"
        ;;
esac

# Create virtual environment
echo ""
echo -e "${YELLOW}Creating virtual environment...${NC}"
python3 -m venv venv

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
if [[ "$OS" == "windows" ]]; then
    source venv/Scripts/activate 2>/dev/null || venv\\Scripts\\activate
else
    source venv/bin/activate
fi

# Upgrade pip
echo ""
echo -e "${YELLOW}Upgrading pip...${NC}"
pip install --upgrade pip

# Install Python dependencies
echo ""
echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to install some dependencies${NC}"
    echo "Trying alternative installation methods..."
    
    # Try installing pyaudio separately
    if [[ "$OS" == "windows" ]]; then
        pip install pipwin
        pipwin install pyaudio
    else
        pip install pyaudio --global-option="build_ext" --global-option="-I/usr/local/include" --global-option="-L/usr/local/lib"
    fi
    
    # Install remaining dependencies
    pip install playwright click rich openai numpy python-dotenv requests
fi

# Install Playwright browsers
echo ""
echo -e "${YELLOW}Installing Chromium browser...${NC}"
playwright install chromium
playwright install-deps

# Create necessary directories
echo ""
echo -e "${YELLOW}Creating directories...${NC}"
mkdir -p logs recordings

# Setup environment file
if [ ! -f .env ]; then
    echo ""
    echo -e "${YELLOW}Creating .env file from template...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✓ Created .env file${NC}"
    echo ""
    echo -e "${YELLOW}Please edit .env and add your API keys:${NC}"
    echo "  - OpenAI API key for audio transcription"
fi

# Make scripts executable
chmod +x run.sh run_dev.sh install.sh 2>/dev/null

# Installation complete
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         Installation Complete!                        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Edit .env file and add your OpenAI API key"
echo "2. Run: ./run.sh help"
echo "3. Start recording: ./run.sh record --project myapp --user me --description 'Test'"
echo ""
echo -e "${GREEN}Happy Testing!${NC}"