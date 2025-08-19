# API Tool CLI - Browser Recording & Security Testing Suite

A powerful command-line tool for browser interaction recording, automated security testing, and audio transcription. Perfect for API testing, security assessments, and creating detailed interaction logs.

## 🚀 Features

- **Lossless Browser Recording**: Captures every browser interaction including clicks, form fills, navigation, and network traffic
- **Audio Narration**: Real-time audio transcription using OpenAI Whisper API
- **Security Testing Integration**: Built-in proxy support for Burp Suite, OWASP ZAP, and other intercepting proxies
- **Rich Terminal UI**: Beautiful command-line interface with progress tracking and interactive menus
- **Comprehensive Logging**: Detailed debug logs for troubleshooting
- **Session Management**: Organize recordings by project and user
- **DOM Tracking**: Captures complete DOM state and changes during interactions

## 📋 Prerequisites

- Python 3.8 or higher
- Linux/macOS/Windows with audio support
- OpenAI API key (for audio transcription)
- PortAudio (for audio recording on Linux)

## 🔧 Installation

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/apitool-cli.git
cd apitool-cli
```

### 2. Set up virtual environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. Linux Audio Setup (if using audio features)
```bash
sudo apt-get install portaudio19-dev python3-pyaudio
```

### 5. Configure environment (optional)
Create a `.env` file for OpenAI API configuration:
```bash
echo "OPENAI_API_KEY=your-api-key-here" > .env
```

## 🎯 Quick Start

### Using the convenience script (recommended)
```bash
# Make the script executable
chmod +x run.sh

# Show help
./run.sh help

# Start interactive menu
./run.sh menu

# Start recording
./run.sh record --project myapp --user john --description "Testing login flow"
```

### Direct Python usage
```bash
# Activate virtual environment
source venv/bin/activate

# Run CLI directly
python -m scripts.cli menu
python -m scripts.cli record --project myapp --user john --description "Testing API endpoints"
```

## 📖 Usage Examples

### Basic Recording
```bash
# Start a recording session with audio
./run.sh record --project webapp --user tester --description "Homepage navigation test"

# Without audio narration
./run.sh record --project webapp --user tester --description "Form submission" --no-audio

# With specific starting URL
./run.sh record --project webapp --user tester --description "Login test" --url https://example.com/login
```

### Security Testing with Proxy
```bash
# Route traffic through Burp Suite
./run.sh record --project security-test --user pentester \
  --description "OWASP Top 10 assessment" \
  --proxy http://127.0.0.1:8080

# Use with OWASP ZAP
./run.sh record --project zap-test --user security \
  --description "Automated scan" \
  --proxy http://127.0.0.1:8090
```

### View Recordings
```bash
# List all recordings for a project
./run.sh record --project webapp

# Access recordings directory
ls recordings/webapp/
```

### Test Components
```bash
# Test browser and audio setup
./run.sh test
```

## 🏗️ Project Structure

```
apitool-cli/
├── scripts/
│   ├── cli.py                 # Main CLI interface
│   ├── browser_recorder.py    # Browser automation logic
│   ├── audio_narrator.py      # Audio recording & transcription
│   ├── recording_manager.py   # Session management
│   └── enumeration/           # Security enumeration tools
├── logs/                      # Debug and error logs
├── recordings/               # Saved recording sessions
├── requirements.txt          # Python dependencies
├── run.sh                   # Convenience launcher script
├── README.md               # This file
└── LICENSE                 # MIT License
```

## 🔐 Security Testing Features

### Proxy Integration
The tool seamlessly integrates with popular security testing proxies:
- Burp Suite Professional/Community
- OWASP ZAP
- mitmproxy
- Charles Proxy

### Captured Data
Each recording session captures:
- Complete HTTP/HTTPS traffic
- DOM snapshots at each interaction
- JavaScript console logs
- Network timing information
- Form data and user inputs
- Cookie changes
- Local/Session storage modifications

### Output Formats
Recordings are saved in structured JSON format containing:
- Timestamp for each action
- Element selectors and attributes
- Network requests and responses
- Audio transcription (if enabled)
- Screenshots at key points

## 🎙️ Audio Features

### Transcription
- Real-time audio capture during browser sessions
- Automatic transcription using OpenAI Whisper API
- Synchronized with browser actions for context
- Cost: ~$0.006 per minute of audio

### Use Cases
- Document testing procedures
- Create training materials
- Generate test evidence
- Voice-guided penetration testing

## 🐛 Troubleshooting

### Common Issues

**Browser won't start**
```bash
# Reinstall Playwright browsers
playwright install chromium --force
```

**Audio not working on Linux**
```bash
# Install audio dependencies
sudo apt-get update
sudo apt-get install portaudio19-dev python3-pyaudio
```

**Permission denied running run.sh**
```bash
chmod +x run.sh
```

**OpenAI API errors**
```bash
# Check your API key
echo $OPENAI_API_KEY
# Set it if missing
export OPENAI_API_KEY="your-key-here"
```

## 📊 Performance

- **Memory usage**: ~200-500MB depending on page complexity
- **CPU usage**: Moderate (15-30% on modern systems)
- **Storage**: ~1-5MB per minute of recording
- **Network overhead**: Minimal when not using proxy

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Playwright](https://playwright.dev/) for browser automation
- [Click](https://click.palletsprojects.com/) for CLI framework
- [Rich](https://rich.readthedocs.io/) for beautiful terminal output
- [OpenAI Whisper](https://openai.com/research/whisper) for audio transcription

## ⚠️ Disclaimer

This tool is intended for authorized security testing and development purposes only. Users are responsible for complying with all applicable laws and obtaining proper authorization before testing any systems they do not own.

## 📧 Support

For issues, questions, or suggestions, please open an issue on GitHub or contact the maintainers.

---

**Note**: This is an MVP tool optimized for rapid prototyping and security testing in controlled environments. Not recommended for production use without additional hardening.