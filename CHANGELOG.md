# Changelog

All notable changes to API Tool CLI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-08-19

### Added
- Initial public release
- Lossless browser recording with Playwright
- Real-time audio narration with OpenAI Whisper
- Rich terminal UI with interactive menus
- Proxy integration for security testing tools
- Session management by project and user
- Comprehensive DOM and interaction tracking
- Detailed logging system
- Support for headless browser mode
- Network traffic capture
- Form interaction recording
- JavaScript console log capture

### Features
- **Browser Recording**: Complete capture of all browser interactions
- **Audio Transcription**: Real-time voice narration during sessions
- **Security Testing**: Built-in proxy support for Burp Suite and OWASP ZAP
- **Session Management**: Organize recordings by project and user
- **Rich CLI**: Beautiful terminal interface with progress tracking
- **Cross-platform**: Support for Linux, macOS, and Windows

### Security
- Proxy support for intercepting HTTPS traffic
- Secure storage of API keys via environment variables
- Sandboxed browser execution

### Documentation
- Comprehensive README with installation and usage instructions
- Contributing guidelines
- MIT License
- Example configurations

## [1.1.0] - 2025-11-18

### Fixed
- HAR files now reliably capture response data during multi-page navigation
- Removed `--start-maximized` flag that caused viewport sizing issues

### Added
- Real-time response capture in `_handle_response` (status, headers, timestamp)
- HAR reconstruction fallback when Playwright's built-in export fails
- New `_reconstruct_har_from_events` function rebuilds HAR from captured events

### Technical Details
- Playwright's HAR export requires a live page when context closes
- Page navigation destroys execution context, breaking HAR export
- Fix captures response data as events occur, then reconstructs HAR if needed
- Tested: 97.4% response capture rate (602/618 entries)

## [Unreleased]

### Planned Features
- Video recording support
- Cloud storage integration
- Team collaboration features
- API endpoint testing automation
- Performance metrics collection
- Custom plugin system
- Report generation
- CI/CD integration improvements

---

## Version History

### Pre-release Development
- 2024-08-14: Project inception
- 2024-08-14: Core browser recording implementation
- 2024-08-14: Audio narration integration
- 2024-08-15: Security enumeration tools added
- 2024-08-19: Prepared for GitHub release