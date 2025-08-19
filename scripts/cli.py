"""Enhanced CLI for Phase 1 Browser Recording - LOSSLESS CAPTURE"""

import asyncio
import logging
import time
import signal
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.prompt import Prompt, Confirm
from rich.live import Live
from rich.layout import Layout

from .browser_recorder import Phase1BrowserRecorder
from .audio_narrator import AudioNarrator
from .recording_manager import RecordingManager

# Comprehensive logging - FILE ONLY for debug, console only for warnings
# Create logs directory if needed
Path('./logs').mkdir(parents=True, exist_ok=True)
# Setup file handler for DEBUG level
file_handler = logging.FileHandler('./logs/cli_enhanced.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s.%(msecs)03d | %(levelname)s | %(funcName)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))

# Setup console handler for WARNING level only
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)
console_handler.setFormatter(logging.Formatter('%(message)s'))

# Configure root logger
logging.basicConfig(
    level=logging.DEBUG,
    handlers=[file_handler, console_handler]
)
logger = logging.getLogger(__name__)

# Global instances for signal handling
browser_recorder = None
audio_narrator = None
recording_active = False

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    global recording_active
    logger.info("Received interrupt signal")
    
    console = Console()
    console.print("\n[yellow]Stopping recording gracefully...[/yellow]")
    
    recording_active = False
    
    # Don't exit here - let the main loop handle cleanup
    # sys.exit(0) removed to allow proper cleanup

@click.group()
def cli():
    """Phase 1 API Tool CLI - LOSSLESS Browser Recording System"""
    pass

@cli.command()
@click.option('--project', required=True, help='Project name for the recording')
@click.option('--user', help='User identifier for the recording')
@click.option('--audio/--no-audio', default=True, help='Enable audio narration during recording')
@click.option('--description', help='Brief description of what you are recording (REQUIRED with --user)')
@click.option('--url', help='Initial URL to navigate to')
@click.option('--headless/--no-headless', default=False, help='Run browser in headless mode')
@click.option('--proxy', help='Proxy URL for intercepting traffic (e.g., http://127.0.0.1:8080 for Burp/ZAP)')
def record(project: str, user: Optional[str], audio: bool, description: Optional[str], url: Optional[str], headless: bool, proxy: Optional[str]):
    """Start LOSSLESS recording session for security testing"""
    global browser_recorder, audio_narrator, recording_active
    
    start_time = time.time()
    console = Console()
    
    # If no user provided, show recordings for the project
    if not user:
        logger.info(f"No user provided, showing recordings for project: {project}")
        manager = RecordingManager(project)
        manager.show_project_recordings()
        return
    
    # User provided, require description
    if not description:
        console.print("[red]Error: --description is required when starting a recording[/red]")
        console.print("[yellow]Usage: ./run.sh record --project PROJECT --user USER --description 'Description'[/yellow]")
        return
    
    logger.info(f"Starting PHASE 1 recording: project={project}, user={user}, audio={audio}, description={description}, proxy={proxy}")
    
    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Check for duplicates within project
    manager = RecordingManager(project)
    if manager.check_duplicate(user, description):
        logger.info("Recording cancelled due to duplicate")
        return
    
    console.print(Panel.fit(
        f"[bold green]Starting Phase 1 LOSSLESS Recording Session[/bold green]\n"
        f"[yellow]Security Testing Mode - NO TRUNCATION[/yellow]\n"
        f"Project: {project}\n"
        f"User: {user}\n"
        f"Description: {description}\n"
        f"Audio: {'Enabled' if audio else 'Disabled'}\n"
        f"Proxy: {proxy if proxy else 'None'}",
        border_style="green"
    ))
    
    async def run_recording(url=url, proxy=proxy):
        global browser_recorder, audio_narrator, recording_active
        
        browser_recorder = Phase1BrowserRecorder(project=project)
        audio_narrator = AudioNarrator(project=project) if audio else None
        recording_active = True
        
        # Track last event for snapshot triggers
        last_api_response = time.time()
        last_form_submit = time.time()
        last_storage_change = time.time()
        
        try:
            # Start browser
            with console.status("[bold green]Opening browser...", spinner="dots"):
                success = await browser_recorder.open_browser(headless=headless, proxy=proxy)
                if not success:
                    console.print("[red]Failed to open browser![/red]")
                    return
            
            console.print("[green]✓[/green] Browser opened")
            
            # Start recording
            with console.status("[bold green]Starting LOSSLESS recording...", spinner="dots"):
                result = await browser_recorder.start_recording(user, description, url)
                if not result["success"]:
                    console.print(f"[red]Failed to start recording: {result.get('error')}[/red]")
                    return
            
            session_id = result["session_id"]
            console.print(f"[green]✓[/green] PHASE 1 Recording started (Session: {session_id})")
            console.print(f"[yellow]📁 Event log: {result['session_dir']}/events.ndjson[/yellow]")
            
            # Start audio if enabled
            audio_result = None
            if audio and audio_narrator:
                with console.status("[bold green]Starting audio recording...", spinner="dots"):
                    # Enable continuous transcription and pass session directory
                    audio_result = audio_narrator.start_recording(
                        session_id, 
                        continuous=True,
                        session_dir=result["session_dir"]  # Pass the session directory from browser recorder
                    )
                    if audio_result["success"]:
                        console.print("[green]✓[/green] Audio recording started")
                    else:
                        console.print(f"[yellow]⚠[/yellow] Audio recording failed: {audio_result.get('error')}")
                        # Don't modify audio variable - it's the parameter
            
            # Simplified recording controls
            console.print("\n[bold cyan]Recording in progress...[/bold cyan]")
            console.print("[yellow]Type 'stop' and press Enter to save recording with HAR file[/yellow]")
            console.print("[dim]Or press Ctrl+C for emergency stop (may skip HAR file)[/dim]")
            console.print("\n[dim]The browser is recording EVERYTHING. No truncation. Full capture.[/dim]")
            
            # Simple status counter with proper line clearing
            start_time = time.time()
            last_status_update = 0
            
            # Setup non-blocking input check
            import select
            import termios
            import tty
            
            # Save terminal settings
            old_settings = termios.tcgetattr(sys.stdin)
            stop_buffer = ""
            
            try:
                # Set terminal to raw mode for non-blocking input
                tty.setcbreak(sys.stdin.fileno())
                
                # Recording loop - EVENT DRIVEN, not timer based
                while recording_active:
                    try:
                        # Check for keyboard input (non-blocking)
                        if select.select([sys.stdin], [], [], 0)[0]:
                            char = sys.stdin.read(1)
                            if char == '\n' or char == '\r':
                                if stop_buffer.strip().lower() == 'stop':
                                    console.print("\n[green]Stop command received - saving recording...[/green]")
                                    recording_active = False
                                    break
                                stop_buffer = ""
                            else:
                                stop_buffer += char
                                # Echo the character
                                print(char, end='', flush=True)
                        
                        # Update status display every second using proper terminal control
                        current_time = time.time()
                        if current_time - last_status_update >= 1:
                            elapsed = int(current_time - start_time)
                            # Clear line and update status - use raw print for terminal control
                            status = f"Recording: {elapsed}s | Events: {browser_recorder.event_counter} | Requests: {browser_recorder.request_count} | WebSockets: {len(browser_recorder.websockets)} | Console: {browser_recorder.console_count}"
                            # Use raw print with ANSI codes for clean updates
                            print(f"\033[2K\r\033[36m{status}\033[0m", end="", flush=True)
                            last_status_update = current_time
                        
                        # Small delay to prevent CPU spinning and check recording_active frequently
                        await asyncio.sleep(0.05)  # Check 20 times per second for faster response
                        
                    except KeyboardInterrupt:
                        # This shouldn't happen since signal handler sets recording_active
                        recording_active = False
                        break
            finally:
                # Restore terminal settings
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            
            # Stop recording with timeout failsafe
            console.print("\n[bold yellow]Stopping PHASE 1 recording...[/bold yellow]")
            
            cleanup_start = time.time()
            max_cleanup_time = 10.0  # Increased to 10 seconds for all cleanup
            
            # Stop audio first
            audio_transcript = None
            if audio and audio_narrator:
                with console.status("[bold green]Stopping audio recording...", spinner="dots"):
                    audio_stop_result = audio_narrator.stop_recording()
                    if audio_stop_result["success"]:
                        console.print(f"[green]✓[/green] Audio saved: {audio_stop_result['audio_path']}")
                        
                        # Transcribe audio with generous timeout
                        # Allow up to 30 seconds for transcription (separate from cleanup timeout)
                        transcription_timeout = 30.0
                        # Show progress bar for transcription
                        with Progress(
                                SpinnerColumn(),
                                TextColumn("[bold green]Transcribing audio..."),
                                BarColumn(),
                                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                                TextColumn("({task.completed:.1f}s / {task.total:.1f}s)"),
                                console=console
                            ) as progress:
                                # Get audio duration for progress tracking
                                import wave
                                with wave.open(audio_stop_result['audio_path'], 'rb') as wf:
                                    frames = wf.getnframes()
                                    rate = wf.getframerate()
                                    audio_duration = frames / float(rate)
                                
                                task = progress.add_task("Transcribing", total=audio_duration)
                                
                                # Create a timeout wrapper for transcription
                                import concurrent.futures
                                with concurrent.futures.ThreadPoolExecutor() as executor:
                                    future = executor.submit(audio_narrator.transcribe, audio_stop_result['audio_path'])
                                    
                                    # Update progress while waiting
                                    start_transcribe = time.time()
                                    while not future.done():
                                        elapsed = time.time() - start_transcribe
                                        progress.update(task, completed=min(elapsed * (audio_duration/transcription_timeout), audio_duration))
                                        time.sleep(0.1)
                                        if elapsed > transcription_timeout:
                                            console.print(f"[yellow]Transcription taking longer than expected...[/yellow]")
                                            break
                                    
                                    try:
                                        # Give transcription more time - up to transcription_timeout seconds
                                        remaining_time = transcription_timeout - (time.time() - start_transcribe)
                                        transcript_result = future.result(timeout=max(0.1, remaining_time))
                                        progress.update(task, completed=audio_duration)
                                        
                                        if transcript_result["success"]:
                                            audio_transcript = transcript_result["text"]
                                            console.print(f"[green]✓[/green] Audio transcribed ({len(transcript_result['segments'])} segments)")
                                            
                                            # Write transcript to event log if we have it
                                            if browser_recorder:
                                                browser_recorder._write_event('audio_transcript', {
                                                    'transcript': audio_transcript,
                                                    'segments': transcript_result['segments']
                                                })
                                        else:
                                            console.print(f"[yellow]⚠[/yellow] Transcription failed: {transcript_result.get('error')}")
                                    except concurrent.futures.TimeoutError:
                                        console.print(f"[yellow]⚠[/yellow] Transcription timed out after {transcription_timeout}s")
            
            # Stop browser recording
            with console.status("[bold green]Finalizing LOSSLESS recording...", spinner="dots"):
                stop_result = await browser_recorder.stop_recording()
                if stop_result["success"]:
                    console.print(f"[green]✓[/green] PHASE 1 Recording saved")
                    console.print(f"  [cyan]Session directory:[/cyan] {stop_result['session_dir']}")
                    console.print(f"  [cyan]Duration:[/cyan] {stop_result['duration']:.1f} seconds")
                    console.print(f"  [cyan]Total events:[/cyan] {stop_result['events_count']}")
                    console.print(f"  [yellow]Event log:[/yellow] events.ndjson (NDJSON format)")
                    console.print(f"  [yellow]HAR file:[/yellow] recording.har (with response bodies)")
                    console.print(f"  [yellow]Blobs:[/yellow] blobs/ directory (large payloads)")
                else:
                    console.print(f"[red]Failed to save recording: {stop_result.get('error')}[/red]")
            
            elapsed = (time.time() - start_time) * 1000
            logger.info(f"PHASE 1 recording session completed in {elapsed:.2f}ms")
            
        finally:
            # Cleanup with timeout protection
            cleanup_tasks = []
            
            async def cleanup_with_timeout():
                try:
                    # Set a maximum cleanup time (separate from transcription)
                    import asyncio
                    
                    if browser_recorder:
                        # Browser cleanup with generous timeout
                        try:
                            await asyncio.wait_for(browser_recorder.cleanup(), timeout=5.0)
                        except asyncio.TimeoutError:
                            logger.warning("Browser cleanup timed out after 5 seconds")
                    
                    if audio_narrator:
                        # Audio cleanup is synchronous, so run it in thread with timeout
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(audio_narrator.cleanup)
                            try:
                                future.result(timeout=1.0)
                            except concurrent.futures.TimeoutError:
                                logger.warning("Audio cleanup timed out")
                    
                except Exception as e:
                    logger.error(f"Cleanup error: {e}")
            
            # Run cleanup with overall timeout
            try:
                await asyncio.wait_for(cleanup_with_timeout(), timeout=3.0)
            except asyncio.TimeoutError:
                logger.warning("Overall cleanup timed out - forcing exit")
                console.print("[yellow]⚠ Cleanup timed out - forcing exit[/yellow]")
    
    # Run the async recording
    try:
        # Use asyncio.run with proper cleanup
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Set custom exception handler to suppress BrokenPipeError
        def exception_handler(loop, context):
            exception = context.get('exception')
            if isinstance(exception, BrokenPipeError):
                # Silently ignore BrokenPipeError during shutdown
                return
            # Log other exceptions at debug level
            logger.debug(f"Event loop exception: {context}")
        
        loop.set_exception_handler(exception_handler)
        
        try:
            loop.run_until_complete(run_recording())
        finally:
            # Cancel all remaining tasks
            try:
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                # Wait for tasks to cancel with timeout
                if pending:
                    # Use wait instead of gather to handle cancellation better
                    loop.run_until_complete(
                        asyncio.wait(pending, timeout=0.5, return_when=asyncio.ALL_COMPLETED)
                    )
            except (BrokenPipeError, ConnectionError):
                # These are expected during shutdown
                pass
            except Exception as e:
                logger.debug(f"Task cleanup error: {e}")
            finally:
                # Suppress BrokenPipeError warnings during loop closure
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", BrokenPipeError)
                    # Close the loop
                    try:
                        loop.close()
                    except Exception:
                        pass
    except Exception as e:
        logger.error(f"Recording failed: {e}")
        console.print(f"[red]Recording failed: {e}[/red]")

@cli.command()
def menu():
    """Show interactive menu with project selection"""
    logger.info("Starting menu command")
    
    console = Console()
    
    while True:
        # First show project selection menu
        manager = RecordingManager()
        project = manager.show_project_menu()
        
        if project == "quit":
            break
        elif project == "new":
            # Create new project
            project_name = Prompt.ask("Enter new project name")
            Path(f"./{project_name}").mkdir(parents=True, exist_ok=True)
            console.print(f"[green]Created new project: {project_name}[/green]")
            project = project_name
        
        # Now show project-specific recordings menu
        project_manager = RecordingManager(project)
        
        while True:
            choice = project_manager.show_menu()
            
            if choice == "1":
                # Start new recording
                console.print(f"\n[cyan]Starting new recording for project: {project}[/cyan]")
                user = Prompt.ask("Enter user identifier")
                description = Prompt.ask("Enter recording description (REQUIRED)")
                use_audio = Confirm.ask("Enable audio narration?", default=True)
                
                # Launch recording
                import subprocess
                cmd = ["python", "cli.py", "record", "--project", project, "--user", user, "--description", description]
                if not use_audio:
                    cmd.append("--no-audio")
                
                console.print(f"[dim]Launching: {' '.join(cmd)}[/dim]")
                subprocess.run(cmd)
            
            elif choice == "2":
                # View recording details
                session_id = Prompt.ask("Enter session ID (or part of it)")
                project_manager.view_recording_details(session_id)
                Prompt.ask("\nPress Enter to continue")
            
            elif choice == "3":
                # Delete recordings
                user = Prompt.ask("Enter user to delete (or 'all' for all recordings)", default="all")
                if user == "all":
                    project_manager.delete_recordings()
                else:
                    project_manager.delete_recordings(user)
                Prompt.ask("\nPress Enter to continue")
            
            elif choice == "4":
                # Export recordings
                output_path = Prompt.ask("Enter output file path", default=None)
                project_manager.export_recordings(output_path)
                Prompt.ask("\nPress Enter to continue")
            
            elif choice == "b":
                # Back to project selection
                break
            
            elif choice == "q":
                console.print("[cyan]Goodbye![/cyan]")
                return
    
    console.print("[cyan]Goodbye![/cyan]")

if __name__ == '__main__':
    cli()