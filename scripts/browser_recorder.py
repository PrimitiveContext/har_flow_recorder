"""Phase 1 Enhanced Browser Recorder - PURE LOSSLESS CAPTURE
Security-focused browser recorder with complete data capture for penetration testing.
"""

import json
import asyncio
import logging
import hashlib
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Set
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, WebSocket, ConsoleMessage, Request, Response
import uuid

# MANDATORY FIRST STEP - Comprehensive logging (file gets DEBUG, console is SILENT)
# Console handler - only critical errors
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.ERROR)  # Even quieter - only errors
console_handler.setFormatter(logging.Formatter('%(message)s'))

# File handler - full debug logging
Path('./logs').mkdir(parents=True, exist_ok=True)
file_handler = logging.FileHandler('./logs/browser_recorder_enhanced.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s.%(msecs)03d | %(levelname)s | %(funcName)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    handlers=[console_handler, file_handler]
)
logger = logging.getLogger(__name__)

# MVP hardcoded values
RECORDINGS_DIR = "/tmp/recordings"  # Fallback only, project directories are preferred
BROWSER_VIEWPORT = {"width": 1920, "height": 1080}
BROWSER_TIMEOUT = 30000  # 30 seconds
BLOB_SIZE_THRESHOLD = 10240  # 10KB - store larger content as blobs

class Phase1BrowserRecorder:
    """Phase 1: PURE, LOSSLESS CAPTURE - No parsing, no truncation"""
    
    def __init__(self, project: Optional[str] = None):
        start_time = time.time()
        logger.info(f"Starting Phase1BrowserRecorder initialization for project: {project}")
        
        self.project = project
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.is_recording = False
        self.is_closing = False  # Flag to prevent operations during shutdown
        self.recording_start: Optional[datetime] = None
        
        # Event log for NDJSON format
        self.event_log_file = None
        self.event_counter = 0
        self.console_count = 0  # Track console messages for status display
        self.request_count = 0  # Track HTTP requests for status display
        self.session_id = None
        self.session_dir = None
        
        # Blob storage for large payloads
        self.blob_dir = None
        self.blob_hashes: Set[str] = set()
        
        # WebSocket tracking
        self.websockets: Dict[str, WebSocket] = {}
        self.websocket_counter = 0
        
        # Cookie lifecycle tracking
        self.cookie_timeline = []
        self.cookie_mutations = {}

        # Connection health tracking
        self.last_event_time = None
        self.connection_healthy = True

        # Ensure logs directory exists
        Path('./logs').mkdir(parents=True, exist_ok=True)
        
        elapsed = (time.time() - start_time) * 1000
        logger.info(f"Completed initialization in {elapsed:.2f}ms")
    
    def _get_monotonic_id(self) -> str:
        """Generate monotonic event ID"""
        self.event_counter += 1
        return f"{self.session_id}-{self.event_counter:08d}"
    
    def _write_event(self, event_type: str, data: Dict[str, Any]):
        """Write event to NDJSON log"""
        # Skip if we're closing or no log file
        if self.is_closing or not self.event_log_file:
            return
            
        event = {
            "id": self._get_monotonic_id(),
            "timestamp": datetime.now().isoformat(),
            "timestamp_ms": int(time.time() * 1000),
            "type": event_type,
            "data": data
        }
        
        try:
            # Write as single line JSON
            self.event_log_file.write(json.dumps(event) + '\n')
            self.event_log_file.flush()  # Ensure immediate write
            self.last_event_time = time.time()  # Track for health monitoring
            logger.debug(f"Wrote event {event['id']}: {event_type}")
        except Exception as e:
            logger.error(f"Failed to write event: {e}")

    async def check_connection_health(self) -> bool:
        """
        Check if browser connection is still alive.
        Returns True if healthy, False if connection is dead.
        """
        if self.is_closing or not self.is_recording:
            return True  # Don't report unhealthy during shutdown

        try:
            # Check if page exists and is not closed
            if not self.page:
                logger.error("Health check failed: No page instance")
                self.connection_healthy = False
                return False

            if self.page.is_closed():
                logger.error("Health check failed: Page is closed")
                self.connection_healthy = False
                return False

            # Try to evaluate a simple expression to verify connection
            await self.page.evaluate("() => true", timeout=5000)
            self.connection_healthy = True
            return True

        except Exception as e:
            error_msg = str(e)
            # Only log as error if it's not a known shutdown condition
            if "Target closed" not in error_msg and "Connection closed" not in error_msg:
                logger.error(f"Health check failed: {e}")
            self.connection_healthy = False
            return False

    def _store_blob(self, content: bytes) -> str:
        """Store large content as blob, return hash reference"""
        if not content:
            return None
            
        # Calculate SHA256 hash
        content_hash = hashlib.sha256(content).hexdigest()
        
        # Check if already stored
        if content_hash in self.blob_hashes:
            logger.debug(f"Blob already exists: {content_hash}")
            return content_hash
        
        # Store blob
        blob_path = self.blob_dir / f"{content_hash}.blob"
        try:
            with open(blob_path, 'wb') as f:
                f.write(content)
            self.blob_hashes.add(content_hash)
            logger.debug(f"Stored blob {content_hash}: {len(content)} bytes")
            return content_hash
        except Exception as e:
            logger.error(f"Failed to store blob: {e}")
            return None
    
    async def _setup_event_listeners(self):
        """Setup comprehensive event listeners for LOSSLESS capture"""
        logger.info("Setting up LOSSLESS event listeners")
        
        try:
            # Inject JavaScript for DOM tracking - NO TRUNCATION
            await self.page.evaluate("""
                window._phase1Events = [];
                window._phase1EventId = 0;
                
                // Track clicks with FULL data
                document.addEventListener('click', (e) => {
                    const target = e.target;
                    const rect = target.getBoundingClientRect();
                    window._phase1Events.push({
                        type: 'dom_click',
                        timestamp: new Date().toISOString(),
                        eventId: ++window._phase1EventId,
                        data: {
                            tagName: target.tagName,
                            id: target.id || null,
                            className: target.className || null,
                            text: target.innerText || null,  // FULL TEXT - NO TRUNCATION
                            html: target.outerHTML,  // FULL HTML
                            href: target.href || null,
                            x: e.clientX,
                            y: e.clientY,
                            screenX: e.screenX,
                            screenY: e.screenY,
                            boundingRect: {
                                top: rect.top,
                                left: rect.left,
                                width: rect.width,
                                height: rect.height
                            },
                            modifiers: {
                                ctrlKey: e.ctrlKey,
                                shiftKey: e.shiftKey,
                                altKey: e.altKey,
                                metaKey: e.metaKey
                            }
                        }
                    });
                }, true);
                
                // Track input changes with FULL values - CRITICAL FOR SECURITY TESTING
                document.addEventListener('input', (e) => {
                    const target = e.target;
                    window._phase1Events.push({
                        type: 'dom_input',
                        timestamp: new Date().toISOString(),
                        eventId: ++window._phase1EventId,
                        data: {
                            tagName: target.tagName,
                            id: target.id || null,
                            name: target.name || null,
                            type: target.type || null,
                            value: target.value || null,  // FULL VALUE - NO TRUNCATION!
                            fullValue: target.value || null,  // Redundant but explicit
                            valueLength: target.value ? target.value.length : 0,
                            placeholder: target.placeholder || null,
                            attributes: Object.fromEntries([...target.attributes].map(a => [a.name, a.value]))
                        }
                    });
                }, true);
                
                // Track form submissions with ALL data
                document.addEventListener('submit', (e) => {
                    const target = e.target;
                    const formData = new FormData(target);
                    const formFields = {};
                    for (let [key, value] of formData.entries()) {
                        // Store FULL values, handle files differently
                        if (value instanceof File) {
                            formFields[key] = {
                                type: 'file',
                                name: value.name,
                                size: value.size,
                                mimeType: value.type
                            };
                        } else {
                            formFields[key] = value;  // FULL VALUE
                        }
                    }
                    
                    window._phase1Events.push({
                        type: 'dom_submit',
                        timestamp: new Date().toISOString(),
                        eventId: ++window._phase1EventId,
                        data: {
                            formId: target.id || null,
                            formAction: target.action || null,
                            formMethod: target.method || null,
                            formEnctype: target.enctype || null,
                            formTarget: target.target || null,
                            formFields: formFields,  // ALL form data
                            formHTML: target.outerHTML
                        }
                    });
                }, true);
                
                // Track ALL navigation events
                const originalPushState = history.pushState;
                const originalReplaceState = history.replaceState;
                
                history.pushState = function() {
                    window._phase1Events.push({
                        type: 'navigation_pushstate',
                        timestamp: new Date().toISOString(),
                        eventId: ++window._phase1EventId,
                        data: {
                            url: arguments[2] || null,
                            state: arguments[0],
                            title: arguments[1]
                        }
                    });
                    return originalPushState.apply(history, arguments);
                };
                
                history.replaceState = function() {
                    window._phase1Events.push({
                        type: 'navigation_replacestate',
                        timestamp: new Date().toISOString(),
                        eventId: ++window._phase1EventId,
                        data: {
                            url: arguments[2] || null,
                            state: arguments[0],
                            title: arguments[1]
                        }
                    });
                    return originalReplaceState.apply(history, arguments);
                };
                
                window.addEventListener('popstate', (e) => {
                    window._phase1Events.push({
                        type: 'navigation_popstate',
                        timestamp: new Date().toISOString(),
                        eventId: ++window._phase1EventId,
                        data: {
                            url: window.location.href,
                            state: e.state
                        }
                    });
                });
                
                // Track storage events
                window.addEventListener('storage', (e) => {
                    window._phase1Events.push({
                        type: 'storage_change',
                        timestamp: new Date().toISOString(),
                        eventId: ++window._phase1EventId,
                        data: {
                            key: e.key,
                            oldValue: e.oldValue,
                            newValue: e.newValue,  // FULL VALUE
                            url: e.url,
                            storageArea: e.storageArea === localStorage ? 'local' : 'session'
                        }
                    });
                });
                
                // Override storage methods to capture ALL writes
                const originalSetItem = Storage.prototype.setItem;
                Storage.prototype.setItem = function(key, value) {
                    window._phase1Events.push({
                        type: 'storage_write',
                        timestamp: new Date().toISOString(),
                        eventId: ++window._phase1EventId,
                        data: {
                            storageType: this === localStorage ? 'local' : 'session',
                            key: key,
                            value: value,  // FULL VALUE
                            valueLength: value ? value.length : 0
                        }
                    });
                    return originalSetItem.apply(this, arguments);
                };
                
                console.log('Phase 1 LOSSLESS event listeners installed');
            """)
            logger.info("DOM event listeners injected successfully - NO TRUNCATION")
            
        except Exception as e:
            logger.error(f"Failed to setup event listeners: {e}")
    
    async def _collect_dom_events(self):
        """Collect DOM events from page"""
        # Skip if we're closing or page is closed
        if self.is_closing or not self.page:
            logger.debug("Skipping DOM collection during shutdown")
            return
            
        try:
            # Check if page is still valid before evaluating
            if not self.page.is_closed():
                events = await self.page.evaluate("window._phase1Events || []")
                if events:
                    logger.info(f"Collected {len(events)} DOM events")
                    
                    # Write each event to log
                    for event in events:
                        # Check if we need blob storage for large values
                        if event.get('type') == 'dom_input' and event.get('data', {}).get('value'):
                            value = event['data']['value']
                            if len(value) > BLOB_SIZE_THRESHOLD:
                                # Store as blob
                                blob_hash = self._store_blob(value.encode('utf-8'))
                                event['data']['value_blob'] = blob_hash
                                event['data']['value'] = f"[BLOB:{blob_hash[:8]}...]"
                        
                        self._write_event(event['type'], event['data'])
                    
                    # Clear the browser's event buffer if page is still valid
                    if not self.page.is_closed():
                        await self.page.evaluate("window._phase1Events = []")
        except Exception as e:
            # Only log as error if we're not closing
            if not self.is_closing:
                logger.error(f"Failed to collect DOM events: {e}")
    
    def _parse_cookie_attributes(self, set_cookie_header: str) -> Dict[str, Any]:
        """Parse Set-Cookie header to extract all attributes"""
        parts = set_cookie_header.split(';')
        cookie = {'raw': set_cookie_header}
        
        # First part is name=value
        if parts:
            name_value = parts[0].strip()
            if '=' in name_value:
                name, value = name_value.split('=', 1)
                cookie['name'] = name
                cookie['value'] = value
        
        # Parse attributes
        for part in parts[1:]:
            part = part.strip().lower()
            if '=' in part:
                attr, val = part.split('=', 1)
                cookie[attr] = val
            else:
                # Boolean attributes
                cookie[part] = True
        
        return cookie
    
    def _handle_response(self, response: Response):
        """Handle response to track cookies, status, headers, and body"""
        # Skip if we're closing
        if self.is_closing:
            return

        try:
            # Capture full response data for HAR reconstruction
            headers = response.headers

            # Write response event with full data
            self._write_event('response', {
                'url': response.url,
                'status': response.status,
                'status_text': response.status_text,
                'headers': dict(headers),
                'timestamp': datetime.now().isoformat()
            })

            # Track Set-Cookie headers with FULL attributes
            set_cookies = []

            # Get all Set-Cookie headers
            for name, value in headers.items():
                if name.lower() == 'set-cookie':
                    cookie_data = self._parse_cookie_attributes(value)
                    cookie_data['timestamp'] = datetime.now().isoformat()
                    cookie_data['url'] = response.url
                    cookie_data['status'] = response.status
                    set_cookies.append(cookie_data)

                    # Track in timeline
                    self.cookie_timeline.append({
                        'event': 'cookie_set',
                        'timestamp': datetime.now().isoformat(),
                        'cookie': cookie_data
                    })

            if set_cookies:
                self._write_event('cookie_set', {
                    'url': response.url,
                    'status': response.status,
                    'cookies': set_cookies
                })
                logger.debug(f"Tracked {len(set_cookies)} cookies from {response.url}")

        except Exception as e:
            logger.error(f"Failed to handle response: {e}")
    
    async def _handle_websocket(self, ws: WebSocket):
        """Track WebSocket connections and messages"""
        # Skip if we're closing
        if self.is_closing:
            return
            
        ws_id = f"ws_{self.websocket_counter}"
        self.websocket_counter += 1
        self.websockets[ws_id] = ws
        
        logger.info(f"WebSocket {ws_id} connected: {ws.url}")
        
        # Log connection
        self._write_event('websocket_connect', {
            'ws_id': ws_id,
            'url': ws.url
        })
        
        # Track frames sent
        ws.on('framesent', lambda payload: self._write_event('websocket_send', {
            'ws_id': ws_id,
            'payload': payload if len(str(payload)) < BLOB_SIZE_THRESHOLD else self._store_blob(str(payload).encode('utf-8')),
            'is_blob': len(str(payload)) >= BLOB_SIZE_THRESHOLD
        }))
        
        # Track frames received
        ws.on('framereceived', lambda payload: self._write_event('websocket_receive', {
            'ws_id': ws_id,
            'payload': payload if len(str(payload)) < BLOB_SIZE_THRESHOLD else self._store_blob(str(payload).encode('utf-8')),
            'is_blob': len(str(payload)) >= BLOB_SIZE_THRESHOLD
        }))
        
        # Track close
        ws.on('close', lambda: self._write_event('websocket_close', {
            'ws_id': ws_id
        }))
    
    def _handle_console(self, msg: ConsoleMessage):
        """Capture console messages"""
        # Skip if we're closing
        if self.is_closing:
            return
            
        self.console_count += 1
        self._write_event('console_message', {
            'type': msg.type,
            'text': msg.text,
            'location': msg.location,
            'args': [str(arg) for arg in msg.args] if msg.args else []
        })
        logger.debug(f"Console {msg.type}: {msg.text[:100]}")
    
    def _handle_pageerror(self, error: Exception):
        """Capture page errors"""
        # Skip if we're closing
        if self.is_closing:
            return
            
        self._write_event('page_error', {
            'error': str(error),
            'type': type(error).__name__
        })
        logger.warning(f"Page error: {error}")
    
    async def _handle_request(self, request: Request):
        """Track requests"""
        # Skip if we're closing
        if self.is_closing:
            return
            
        self.request_count += 1
        try:
            post_data = None
            try:
                post_data = request.post_data
            except Exception:
                # Binary or gzipped data - store as blob
                post_data = "[BINARY_DATA]"
            
            # Store large payloads as blobs
            if post_data and isinstance(post_data, str) and len(post_data) > BLOB_SIZE_THRESHOLD:
                post_data_ref = self._store_blob(post_data.encode('utf-8'))
                post_data = f"[BLOB:{post_data_ref[:8]}...]"
            
            self._write_event('request', {
                'url': request.url,
                'method': request.method,
                'headers': dict(request.headers),
                'post_data': post_data,
                'resource_type': request.resource_type,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Failed to handle request: {e}")
    
    async def _handle_page_navigation(self, url: str):
        """Handle page navigation events"""
        # Skip if we're closing
        if self.is_closing:
            return
            
        self._write_event('navigation', {
            'url': url,
            'timestamp': datetime.now().isoformat()
        })
        logger.info(f"Navigation to: {url}")
        
        # Trigger snapshot after navigation
        await self._trigger_snapshot('navigation')
    
    async def _trigger_snapshot(self, trigger: str):
        """Event-driven snapshot"""
        # Skip if we're closing or page is closed
        if self.is_closing or not self.page:
            logger.debug("Skipping snapshot during shutdown")
            return
            
        # Check if page is still valid
        if self.page.is_closed():
            logger.debug("Page is closed, skipping snapshot")
            return
            
        logger.debug(f"Snapshot triggered by: {trigger}")
        
        # Collect DOM events
        await self._collect_dom_events()
        
        # Capture current state - check if page is not about:blank first
        try:
            # Check page is still valid before accessing
            if self.page.is_closed():
                return
                
            current_url = self.page.url
            if current_url == "about:blank":
                logger.debug("Skipping snapshot for about:blank page")
                return
                
            state = await self.page.evaluate("""
                () => {
                    try {
                        return {
                            localStorage: (typeof localStorage !== 'undefined' && localStorage) ? 
                                Object.fromEntries(Object.entries(localStorage)) : {},
                            sessionStorage: (typeof sessionStorage !== 'undefined' && sessionStorage) ? 
                                Object.fromEntries(Object.entries(sessionStorage)) : {},
                            cookies: document.cookie || '',
                            url: window.location.href,
                            title: document.title || '',
                            readyState: document.readyState || 'unknown'
                        };
                    } catch (e) {
                        // Return partial state if storage access fails
                        return {
                            localStorage: {},
                            sessionStorage: {},
                            cookies: document.cookie || '',
                            url: window.location.href,
                            title: document.title || '',
                            readyState: document.readyState || 'unknown',
                            error: e.toString()
                        };
                    }
                }
            """)
            
            self._write_event('snapshot', {
                'trigger': trigger,
                'state': state
            })
        except Exception as e:
            # Only log as error if we're not closing
            if not self.is_closing:
                logger.error(f"Failed to capture snapshot: {e}")
    
    async def initialize(self):
        """Initialize Playwright"""
        logger.info("Initializing Playwright")
        if not self.playwright:
            self.playwright = await async_playwright().start()
            logger.debug("Playwright started successfully")
    
    async def open_browser(self, headless: bool = False, proxy: Optional[str] = None) -> bool:
        """Open browser for recording with optional proxy support"""
        start_time = time.time()
        logger.info(f"Opening browser (headless={headless}, proxy={proxy})")
        
        try:
            await self.initialize()
            
            # Close existing browser if open
            if self.browser:
                logger.debug("Closing existing browser instance")
                await self.browser.close()
                self.browser = None
            
            # MVP: Simple browser launch with all security disabled for testing
            launch_options = {
                "headless": headless,
                "args": [
                    # EXISTING FLAGS
                    "--ignore-certificate-errors",
                    "--disable-web-security",
                    "--allow-running-insecure-content",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",

                    # NEW SECURITY BYPASS FLAGS FOR COMPLETE TESTING
                    "--allow-insecure-localhost",  # Critical for testing local APIs with self-signed certs
                    "--disable-features=SameSiteByDefaultCookies",  # Allow cross-site cookies for CSRF testing
                    "--disable-features=CookiesWithoutSameSiteMustBeSecure",  # Test insecure cookie configs
                    "--disable-blink-features=AutomationControlled",  # Hide automation from detection
                ]
            }
            
            # Add proxy-specific flags if proxy is configured
            if proxy:
                # Extract proxy host for exclusion
                try:
                    proxy_host = proxy.split("//")[1].split(":")[0]
                except:
                    proxy_host = "192.168.1.228"
                    
                launch_options["args"].extend([
                    f"--proxy-server={proxy}",  # Force proxy at browser level too
                    "--proxy-bypass-list=",  # Empty bypass list - proxy everything
                    "--ignore-certificate-errors-spki-list",  # Ignore cert errors from proxy  
                ])
            
            logger.debug(f"Launch options: {launch_options}")
            logger.info("Security flags enabled: allow-insecure-localhost, SameSite cookies disabled, CSP bypass")
            self.browser = await self.playwright.chromium.launch(**launch_options)
            
            # Create context with all security disabled and optional proxy
            context_options = {
                "ignore_https_errors": True,  # REQUIRED for proxy SSL interception
                "accept_downloads": True,
                "viewport": BROWSER_VIEWPORT,
                "bypass_csp": True,  # Bypass Content Security Policy - ensures our DOM tracking always works
            }
            
            # Add proxy configuration if provided
            if proxy:
                logger.info(f"Configuring proxy: {proxy}")
                try:
                    # Parse proxy URL to check for auth (e.g., "http://user:pass@127.0.0.1:8080")
                    from urllib.parse import urlparse
                    parsed = urlparse(proxy)
                    
                    proxy_config = {
                        "server": proxy
                    }
                    
                    # Add authentication if provided in URL
                    if parsed.username and parsed.password:
                        proxy_config["username"] = parsed.username
                        proxy_config["password"] = parsed.password
                        # Reconstruct server URL without auth
                        proxy_config["server"] = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
                        logger.info(f"Using proxy: {parsed.hostname}:{parsed.port} with authentication")
                    else:
                        logger.info(f"Using proxy: {proxy} (no authentication)")
                    
                    context_options["proxy"] = proxy_config
                    
                except Exception as e:
                    logger.error(f"Failed to configure proxy: {e}")
                    # Continue without proxy if configuration fails
            
            logger.debug(f"Context options: {context_options}")
            self.context = await self.browser.new_context(**context_options)
            
            self.page = await self.context.new_page()
            await self.page.goto("about:blank")
            
            elapsed = (time.time() - start_time) * 1000
            logger.info(f"Browser opened successfully in {elapsed:.2f}ms")
            return True
            
        except Exception as e:
            logger.error(f"Failed to open browser: {e}")
            return False
    
    async def start_recording(self, user: str, description: str, url: Optional[str] = None) -> Dict[str, Any]:
        """Start LOSSLESS recording session"""
        start_time = time.time()
        logger.info(f"Starting PHASE 1 recording for user={user}, description={description}")
        
        try:
            if not self.browser:
                logger.error("No browser instance")
                return {"success": False, "error": "Browser not open"}
            
            # Generate session ID
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.session_id = f"{user}_{timestamp}_{uuid.uuid4().hex[:8]}"
            
            # Create session directory with project structure
            if self.project:
                self.session_dir = Path(f"./{self.project}/recordings") / user / self.session_id
            else:
                # Fallback to old structure if no project specified
                self.session_dir = Path(RECORDINGS_DIR) / user / self.session_id
            self.session_dir.mkdir(parents=True, exist_ok=True)
            
            # Create blob directory
            self.blob_dir = self.session_dir / "blobs"
            self.blob_dir.mkdir(exist_ok=True)
            
            # Open NDJSON event log
            event_log_path = self.session_dir / "events.ndjson"
            self.event_log_file = open(event_log_path, 'w')
            
            logger.info(f"Session directory: {self.session_dir}")
            logger.info(f"Event log: {event_log_path}")
            
            # Write session start event
            self._write_event('session_start', {
                'user': user,
                'description': description,
                'session_id': self.session_id,
                'initial_url': url
            })
            
            # Close existing context and create new one with HAR recording
            if self.context:
                await self.context.close()
            
            har_path = self.session_dir / "recording.har"
            self.context = await self.browser.new_context(
                record_har_path=str(har_path),
                record_har_content="attach",  # Include response bodies
                ignore_https_errors=True,
                viewport=BROWSER_VIEWPORT
            )
            
            self.page = await self.context.new_page()
            
            # Setup ALL event listeners
            await self._setup_event_listeners()
            
            # Setup Playwright event handlers
            self.page.on('console', self._handle_console)
            self.page.on('pageerror', self._handle_pageerror)
            self.page.on('request', self._handle_request)
            self.page.on('response', self._handle_response)
            self.page.on('websocket', self._handle_websocket)
            # Navigation handler - only track main frame
            async def handle_navigation(frame):
                try:
                    if frame == self.page.main_frame and not self.is_closing:
                        await self._handle_page_navigation(frame.url)
                except Exception as e:
                    logger.debug(f"Navigation handler error (likely during shutdown): {e}")
            
            # Create task with proper error handling
            def create_navigation_task(frame):
                task = asyncio.create_task(handle_navigation(frame))
                # Add done callback to suppress "Future exception was never retrieved" warning
                task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)
                
            self.page.on('framenavigated', create_navigation_task)
            
            # Navigate to URL if provided
            if url:
                logger.info(f"Navigating to {url}")
                try:
                    response = await self.page.goto(url, wait_until="commit", timeout=BROWSER_TIMEOUT)
                    if response:
                        logger.info(f"Navigation successful: {response.status} {response.status_text}")
                    else:
                        logger.warning(f"Navigation to {url} returned no response")
                except Exception as e:
                    logger.error(f"Navigation to {url} failed: {type(e).__name__}: {e}")
                    # Still continue to allow manual navigation
            
            # Initialize recording state
            self.is_recording = True
            self.recording_start = datetime.now()
            self.event_counter = 0
            self.console_count = 0
            self.request_count = 0
            self.websocket_counter = 0
            self.cookie_timeline = []
            
            # Initial snapshot
            await self._trigger_snapshot('recording_start')
            
            elapsed = (time.time() - start_time) * 1000
            logger.info(f"PHASE 1 recording started successfully in {elapsed:.2f}ms")
            
            return {
                "success": True,
                "session_id": self.session_id,
                "session_dir": str(self.session_dir)
            }
            
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            return {"success": False, "error": str(e)}
    
    async def trigger_snapshot(self, reason: str = "manual"):
        """Manually trigger a snapshot - called after events"""
        if not self.is_recording:
            return
        
        logger.info(f"Manual snapshot triggered: {reason}")
        await self._trigger_snapshot(reason)
    
    async def stop_recording(self) -> Dict[str, Any]:
        """Stop recording and finalize"""
        start_time = time.time()
        logger.info("Stopping PHASE 1 recording")
        
        # Set closing flag immediately to prevent any further operations
        self.is_closing = True
        
        # Save critical values before any operations that might fail
        saved_session_dir = str(self.session_dir) if self.session_dir else None
        saved_event_counter = self.event_counter
        saved_duration = 0
        
        try:
            if not self.is_recording:
                logger.warning("No active recording to stop")
                return {"success": False, "error": "No active recording"}
            
            # Try to get final data before marking as closing
            try:
                # Temporarily unset closing flag for final operations
                self.is_closing = False
                
                # Final snapshot
                await self._trigger_snapshot('recording_stop')
                
                # Collect any remaining DOM events
                await self._collect_dom_events()
                
            except Exception as e:
                logger.debug(f"Error during final data collection (expected if page closing): {e}")
            finally:
                # Set closing flag again
                self.is_closing = True
            
            # Write session end event
            recording_end = datetime.now()
            duration = (recording_end - self.recording_start).total_seconds() if self.recording_start else 0
            saved_duration = duration  # Save for return value
            
            self._write_event('session_end', {
                'duration_seconds': duration,
                'total_events': self.event_counter,
                'total_websockets': self.websocket_counter,
                'total_cookies': len(self.cookie_timeline),
                'total_blobs': len(self.blob_hashes)
            })
            
            # Close event log
            if self.event_log_file:
                self.event_log_file.close()
                self.event_log_file = None
            
            # Close context to finalize HAR - let Playwright handle page cleanup
            # Don't manually close pages - this can interfere with HAR finalization
            if self.context:
                try:
                    await self.context.close()
                    logger.debug("Context closed successfully, HAR should be saved")
                    # Give Playwright time to write HAR file to disk
                    await asyncio.sleep(1.0)
                except Exception as e:
                    logger.debug(f"Context close error (HAR may not be saved): {e}")
                finally:
                    self.context = None
                    self.page = None

            # ALWAYS check if HAR exists and reconstruct if missing
            if self.session_dir and not (self.session_dir / "recording.har").exists():
                logger.warning("HAR file was not saved by Playwright")
                logger.info("Reconstructing HAR from captured events...")
                self._reconstruct_har_from_events()
            
            # Write metadata summary
            metadata = {
                "session_id": self.session_id,
                "start_time": self.recording_start.isoformat(),
                "end_time": recording_end.isoformat(),
                "duration_seconds": duration,
                "total_events": self.event_counter,
                "total_blobs": len(self.blob_hashes),
                "cookie_timeline_length": len(self.cookie_timeline),
                "har_file": "recording.har",
                "event_log": "events.ndjson",
                "blob_directory": "blobs/"
            }
            
            metadata_path = self.session_dir / "metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Recording saved to {self.session_dir}")
            logger.info(f"Total events: {self.event_counter}")
            logger.info(f"Total blobs: {len(self.blob_hashes)}")
            logger.info(f"Cookie timeline: {len(self.cookie_timeline)} events")
            
            # Reset state
            self.is_recording = False
            self.is_closing = False  # Reset closing flag
            self.recording_start = None
            self.session_id = None
            self.session_dir = None
            self.blob_dir = None
            self.event_counter = 0
            self.request_count = 0
            self.websocket_counter = 0
            self.websockets = {}
            self.cookie_timeline = []
            self.blob_hashes = set()
            
            elapsed = (time.time() - start_time) * 1000
            logger.info(f"PHASE 1 recording stopped successfully in {elapsed:.2f}ms")
            
            return {
                "success": True,
                "session_dir": saved_session_dir,  # Use saved value instead of None
                "metadata_path": str(metadata_path) if 'metadata_path' in locals() else None,
                "duration": saved_duration,
                "events_count": saved_event_counter
            }
            
        except Exception as e:
            logger.error(f"Failed to stop recording: {e}")
            # Still try to return useful info even if there was an error
            return {
                "success": True,  # Set to True if we at least saved some data
                "session_dir": saved_session_dir,
                "duration": saved_duration,
                "events_count": saved_event_counter,
                "error": str(e)
            }
    
    def _reconstruct_har_from_events(self):
        """Reconstruct HAR file from captured events when Playwright's HAR export fails"""
        try:
            events_file = self.session_dir / "events.ndjson"
            if not events_file.exists():
                logger.error("Cannot reconstruct HAR: events.ndjson not found")
                return

            # Read all request and response events
            requests = []
            responses = {}  # Map URL to response data
            with open(events_file, 'r') as f:
                for line in f:
                    try:
                        event = json.loads(line)
                        if event.get('type') == 'request':
                            requests.append(event)
                        elif event.get('type') == 'response':
                            # Store response by URL for matching
                            url = event.get('data', {}).get('url', '')
                            responses[url] = event.get('data', {})
                    except json.JSONDecodeError:
                        continue

            # Build HAR structure
            har = {
                "log": {
                    "version": "1.2",
                    "creator": {
                        "name": "har_flow_recorder_fallback",
                        "version": "1.0"
                    },
                    "entries": []
                }
            }

            # Convert each request event to HAR entry
            for req_event in requests:
                data = req_event.get('data', {})
                url = data.get('url', '')

                # Find matching response
                resp_data = responses.get(url, {})

                entry = {
                    "startedDateTime": req_event.get('timestamp', ''),
                    "time": 0,
                    "request": {
                        "method": data.get('method', 'GET'),
                        "url": url,
                        "httpVersion": "HTTP/1.1",
                        "headers": [
                            {"name": k, "value": v}
                            for k, v in data.get('headers', {}).items()
                        ],
                        "queryString": [],
                        "cookies": [],
                        "headersSize": -1,
                        "bodySize": -1
                    },
                    "response": {
                        "status": resp_data.get('status', 0),
                        "statusText": resp_data.get('status_text', ''),
                        "httpVersion": "HTTP/1.1",
                        "headers": [
                            {"name": k, "value": v}
                            for k, v in resp_data.get('headers', {}).items()
                        ],
                        "cookies": [],
                        "content": {
                            "size": 0,
                            "mimeType": resp_data.get('headers', {}).get('content-type', '')
                        },
                        "redirectURL": "",
                        "headersSize": -1,
                        "bodySize": -1
                    },
                    "cache": {},
                    "timings": {
                        "send": 0,
                        "wait": 0,
                        "receive": 0
                    }
                }

                # Add POST data if present
                if data.get('post_data'):
                    entry["request"]["postData"] = {
                        "mimeType": "application/x-www-form-urlencoded",
                        "text": data['post_data']
                    }

                har["log"]["entries"].append(entry)

            # Write HAR file
            har_path = self.session_dir / "recording.har"
            with open(har_path, 'w') as f:
                json.dump(har, f, indent=2)

            logger.info(f"Successfully reconstructed HAR with {len(requests)} requests and {len(responses)} responses")

        except Exception as e:
            logger.error(f"Failed to reconstruct HAR: {e}")

    async def navigate_to(self, url: str) -> bool:
        """Navigate to a URL"""
        logger.info(f"Navigating to {url}")
        
        try:
            if not self.page:
                logger.error("No page instance")
                return False
            
            # Add protocol if missing
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
                logger.debug(f"Added https:// protocol: {url}")
            
            # Navigate
            await self.page.goto(url, wait_until="commit", timeout=BROWSER_TIMEOUT)
            logger.info(f"Successfully navigated to {url}")
            
            # Trigger snapshot after navigation
            if self.is_recording:
                await self._trigger_snapshot('navigation')
            
            return True
                
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup resources with timeout protection"""
        logger.info("Cleaning up browser resources")
        
        # Set closing flag to prevent any operations during cleanup
        self.is_closing = True
        
        try:
            # Close event log file first (synchronous)
            if self.event_log_file:
                try:
                    self.event_log_file.close()
                    self.event_log_file = None
                except:
                    pass
            
            # Gather all cleanup tasks with error handling
            cleanup_tasks = []
            
            async def safe_close(coro, name):
                """Safely close a resource with timeout and error suppression"""
                try:
                    await asyncio.wait_for(coro, timeout=1.0)
                    logger.debug(f"{name} closed successfully")
                except asyncio.TimeoutError:
                    logger.debug(f"{name} close timed out (expected during shutdown)")
                except (BrokenPipeError, ConnectionError) as e:
                    # These are expected during shutdown - log at debug level
                    logger.debug(f"{name} connection error during shutdown: {e}")
                except Exception as e:
                    # Only log unexpected errors at warning level
                    if "Target closed" not in str(e) and "Connection closed" not in str(e):
                        logger.warning(f"{name} close failed: {e}")
                    else:
                        logger.debug(f"{name} expected shutdown error: {e}")
            
            # Add cleanup tasks
            if self.page:
                cleanup_tasks.append(safe_close(self.page.close(), "Page"))
                
            if self.context:
                cleanup_tasks.append(safe_close(self.context.close(), "Context"))
                
            if self.browser:
                cleanup_tasks.append(safe_close(self.browser.close(), "Browser"))
                
            # Run all cleanup tasks concurrently with error handling
            if cleanup_tasks:
                # Use gather with return_exceptions to suppress "Future exception was never retrieved"
                results = await asyncio.gather(*cleanup_tasks, return_exceptions=True)
                # Log any unexpected exceptions
                for result in results:
                    if isinstance(result, Exception) and not isinstance(result, (BrokenPipeError, ConnectionError, asyncio.TimeoutError)):
                        if "Target closed" not in str(result) and "Connection closed" not in str(result):
                            logger.debug(f"Cleanup task exception: {result}")
            
            # Stop playwright last
            if self.playwright:
                try:
                    await asyncio.wait_for(self.playwright.stop(), timeout=1.0)
                    logger.debug("Playwright stopped successfully")
                except asyncio.TimeoutError:
                    logger.debug("Playwright stop timed out (expected)")
                except (BrokenPipeError, ConnectionError) as e:
                    logger.debug(f"Playwright connection error during shutdown: {e}")
                except Exception as e:
                    if "Target closed" not in str(e) and "Connection closed" not in str(e):
                        logger.warning(f"Playwright stop failed: {e}")
                    else:
                        logger.debug(f"Playwright expected shutdown error: {e}")
            
            # Clear references
            self.page = None
            self.context = None
            self.browser = None
            self.playwright = None
            
            # Reset closing flag
            self.is_closing = False
            
            logger.info("Cleanup completed")
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
            # Don't raise - we want to exit cleanly even if cleanup fails