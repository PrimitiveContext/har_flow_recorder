# Contributing to API Tool CLI

First off, thank you for considering contributing to API Tool CLI! It's people like you that make this tool better for everyone.

## Code of Conduct

By participating in this project, you are expected to uphold our values of respect, inclusivity, and collaboration.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When you create a bug report, include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples**
- **Describe the behavior you observed and what you expected**
- **Include logs from the `logs/` directory**
- **Include your environment details** (OS, Python version, etc.)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion:

- **Use a clear and descriptive title**
- **Provide a detailed description of the suggested enhancement**
- **Provide specific examples to demonstrate the enhancement**
- **Describe the current behavior and expected behavior**
- **Explain why this enhancement would be useful**

### Pull Requests

1. Fork the repo and create your branch from `main`
2. If you've added code that should be tested, add tests
3. Ensure the test suite passes
4. Make sure your code follows the existing style
5. Issue that pull request!

## Development Setup

1. Fork and clone the repository
```bash
git clone https://github.com/yourusername/apitool-cli.git
cd apitool-cli
```

2. Create a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install development dependencies
```bash
pip install -r requirements.txt
pip install pytest pytest-asyncio black flake8 mypy
playwright install chromium
```

4. Create a branch for your feature
```bash
git checkout -b feature/your-feature-name
```

## Testing

Run the test suite:
```bash
python -m pytest tests/ -v
```

Run specific tests:
```bash
python -m pytest tests/test_browser_recorder.py -v
```

## Code Style

We use Black for code formatting and Flake8 for linting:

```bash
# Format code
black scripts/

# Check linting
flake8 scripts/ --max-line-length=120
```

## Project Structure

```
apitool-cli/
├── scripts/           # Main source code
│   ├── cli.py        # CLI entry point
│   ├── browser_recorder.py
│   ├── audio_narrator.py
│   └── recording_manager.py
├── tests/            # Test files
├── logs/            # Runtime logs
└── recordings/      # Output directory
```

## Commit Messages

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line

## Documentation

- Update the README.md with details of changes to the interface
- Update docstrings for any new or modified functions
- Comment your code where necessary
- Update the CHANGELOG.md with your changes

## Questions?

Feel free to open an issue with your questions or reach out to the maintainers.

Thank you for contributing!