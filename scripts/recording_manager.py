"""Recording manager with project-based menu and coverage tracking"""

import json
import logging
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

# Comprehensive logging
from pathlib import Path
Path('./logs').mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d | %(levelname)s | %(funcName)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('./logs/recording_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RecordingManager:
    def __init__(self, project: Optional[str] = None):
        start_time = time.time()
        logger.info(f"Starting RecordingManager initialization for project: {project}")
        
        self.console = Console()
        self.project = project
        
        if project:
            # Project-specific recordings directory
            self.recordings_dir = Path(f"./{project}/recordings")
            self.recordings_dir.mkdir(parents=True, exist_ok=True)
        else:
            # Base directory for project listing
            self.recordings_dir = Path(".")
        
        elapsed = (time.time() - start_time) * 1000
        logger.info(f"Completed initialization in {elapsed:.2f}ms")
    
    def show_project_menu(self) -> str:
        """Show menu for selecting or creating a project"""
        logger.info("Displaying project selection menu")
        
        self.console.clear()
        
        # Title
        self.console.print(Panel.fit(
            "[bold cyan]API Tool CLI - Project Selection[/bold cyan]",
            border_style="cyan"
        ))
        
        # Scan for existing projects
        projects = []
        for item in Path(".").iterdir():
            if item.is_dir() and not item.name.startswith('.') and not item.name.startswith('venv'):
                # Check if it has recordings directory
                recordings_dir = item / "recordings"
                if recordings_dir.exists() or (item / "metadata.json").exists():
                    projects.append(item.name)
        
        if projects:
            self.console.print("\n[bold]Existing Projects:[/bold]")
            for i, project in enumerate(projects, 1):
                # Get recording count
                recordings_dir = Path(f"./{project}/recordings")
                recording_count = 0
                if recordings_dir.exists():
                    for user_dir in recordings_dir.iterdir():
                        if user_dir.is_dir():
                            recording_count += len(list(user_dir.glob("*/metadata.json")))
                
                self.console.print(f"  [cyan]{i}[/cyan] - {project} ({recording_count} recordings)")
        else:
            self.console.print("\n[yellow]No existing projects found.[/yellow]")
        
        # Menu options
        self.console.print("\n[bold]Options:[/bold]")
        if projects:
            self.console.print("  [cyan]Select number[/cyan] - Choose existing project")
        self.console.print("  [cyan]n[/cyan] - Create new project")
        self.console.print("  [cyan]q[/cyan] - Quit")
        
        # Get choice
        if projects:
            valid_choices = [str(i) for i in range(1, len(projects) + 1)] + ["n", "q"]
            choice = Prompt.ask("\n[bold]Choose option[/bold]", choices=valid_choices)
            
            if choice.isdigit():
                selected_project = projects[int(choice) - 1]
                logger.info(f"Selected project: {selected_project}")
                return selected_project
            elif choice == "n":
                return "new"
            else:
                return "quit"
        else:
            choice = Prompt.ask("\n[bold]Choose option[/bold]", choices=["n", "q"])
            return "new" if choice == "n" else "quit"
    
    def show_project_recordings(self):
        """Show recordings for current project (when no user specified)"""
        if not self.project:
            self.console.print("[red]No project specified![/red]")
            return
        
        self.console.clear()
        self.console.print(Panel.fit(
            f"[bold cyan]Project: {self.project} - Recordings[/bold cyan]",
            border_style="cyan"
        ))
        
        recordings = self._scan_recordings()
        
        if not recordings:
            self.console.print("\n[yellow]No recordings found for this project.[/yellow]")
            self.console.print("[dim]Start a recording with: ./run.sh record --project {self.project} --user USER --description 'Description'[/dim]")
            return
        
        # Create table
        table = Table(
            title=f"All Recordings in {self.project}",
            box=box.ROUNDED,
            show_lines=True
        )
        
        table.add_column("User", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")
        table.add_column("Duration", justify="center")
        table.add_column("Events", justify="center")
        table.add_column("Requests", justify="center")
        table.add_column("WebSockets", justify="center")
        table.add_column("Console", justify="center")
        
        for user, user_recordings in recordings.items():
            for rec in user_recordings:
                # Format duration in MM:SS
                duration = rec.get("duration_seconds", 0)
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                duration_str = f"{minutes}:{seconds:02d}"
                
                table.add_row(
                    user,
                    rec.get("description", "No description"),
                    duration_str,
                    str(rec.get("events_count", 0)),
                    str(rec.get("requests_count", 0)),
                    str(rec.get("websockets_count", 0)),
                    str(rec.get("console_count", 0))
                )
        
        self.console.print("\n")
        self.console.print(table)
    
    def _scan_recordings(self) -> Dict[str, List[Dict[str, Any]]]:
        """Scan directory for existing recordings in project structure"""
        logger.info(f"Scanning recordings in {self.recordings_dir}")
        
        recordings = {}
        
        if not self.recordings_dir.exists():
            return recordings
        
        try:
            # Project structure: project/recordings/user/session/
            for user_dir in self.recordings_dir.iterdir():
                if user_dir.is_dir() and not user_dir.name.startswith('.'):
                    user = user_dir.name
                    recordings[user] = []
                    
                    for session_dir in user_dir.iterdir():
                        if session_dir.is_dir():
                            metadata_file = session_dir / "metadata.json"
                            if metadata_file.exists():
                                try:
                                    with open(metadata_file, 'r') as f:
                                        metadata = json.load(f)
                                        
                                        # Add metrics from events.ndjson if available
                                        events_file = session_dir / "events.ndjson"
                                        if events_file.exists():
                                            events_count = 0
                                            requests_count = 0
                                            websockets_count = 0
                                            console_count = 0
                                            
                                            with open(events_file, 'r') as ef:
                                                for line in ef:
                                                    try:
                                                        event = json.loads(line)
                                                        events_count += 1
                                                        event_type = event.get('type', '')
                                                        if event_type.startswith('request'):
                                                            requests_count += 1
                                                        elif event_type.startswith('websocket'):
                                                            websockets_count += 1
                                                        elif event_type == 'console':
                                                            console_count += 1
                                                    except:
                                                        pass
                                            
                                            metadata['events_count'] = events_count
                                            metadata['requests_count'] = requests_count
                                            metadata['websockets_count'] = websockets_count
                                            metadata['console_count'] = console_count
                                        
                                        recordings[user].append({
                                            "session_id": session_dir.name,
                                            "path": str(session_dir),
                                            **metadata
                                        })
                                except Exception as e:
                                    logger.warning(f"Failed to read {metadata_file}: {e}")
                                    continue
            
            total = sum(len(v) for v in recordings.values())
            logger.info(f"Found {total} recordings across {len(recordings)} users")
            
        except Exception as e:
            logger.error(f"Error scanning recordings: {e}")
        
        return recordings
    
    def _calculate_coverage(self, recordings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate coverage statistics for a user"""
        logger.debug(f"Calculating coverage for {len(recordings)} recordings")
        
        coverage = {
            "total_recordings": len(recordings),
            "total_duration": 0,
            "total_events": 0,
            "total_requests": 0,
            "unique_urls": set(),
            "features_covered": set(),
            "last_recording": None
        }
        
        for rec in recordings:
            coverage["total_duration"] += rec.get("duration_seconds", 0)
            coverage["total_events"] += rec.get("events_count", 0)
            coverage["total_requests"] += rec.get("requests_count", 0)
            
            # Extract features from description
            if "description" in rec:
                coverage["features_covered"].add(rec["description"])
            
            # Track last recording time
            if rec.get("start_time"):
                if not coverage["last_recording"] or rec["start_time"] > coverage["last_recording"]:
                    coverage["last_recording"] = rec["start_time"]
        
        # Convert sets to lists for display
        coverage["unique_urls"] = len(coverage["unique_urls"])
        coverage["features_covered"] = list(coverage["features_covered"])
        
        logger.debug(f"Coverage: {coverage['total_recordings']} recordings, {coverage['total_events']} events")
        
        return coverage
    
    def show_menu(self) -> Optional[str]:
        """Display interactive menu with recordings and coverage for current project"""
        logger.info(f"Displaying recording menu for project: {self.project}")
        
        self.console.clear()
        
        # Title
        self.console.print(Panel.fit(
            f"[bold cyan]Project: {self.project} - Recording Manager[/bold cyan]",
            border_style="cyan"
        ))
        
        # Scan for recordings
        with self.console.status("[bold green]Scanning recordings...", spinner="dots"):
            recordings = self._scan_recordings()
        
        if not recordings:
            self.console.print("\n[yellow]No recordings found yet![/yellow]\n")
        else:
            # Create coverage table
            table = Table(
                title="Recording Coverage by User",
                box=box.ROUNDED,
                show_lines=True
            )
            
            table.add_column("User", style="cyan", no_wrap=True)
            table.add_column("Recordings", justify="center")
            table.add_column("Total Duration", justify="center")
            table.add_column("Total Events", justify="center")
            table.add_column("Features", justify="left")
            table.add_column("Last Recording", style="dim")
            
            for user, user_recordings in recordings.items():
                coverage = self._calculate_coverage(user_recordings)
                
                # Format duration in MM:SS
                duration = coverage["total_duration"]
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                duration_str = f"{minutes}:{seconds:02d}"
                
                # Format features
                features = coverage["features_covered"][:3]  # Show first 3
                if len(coverage["features_covered"]) > 3:
                    features.append(f"+{len(coverage['features_covered'])-3} more")
                features_str = "\n".join(features) if features else "None"
                
                # Format last recording
                last_rec = coverage["last_recording"]
                if last_rec:
                    last_dt = datetime.fromisoformat(last_rec.replace('Z', '+00:00'))
                    last_str = last_dt.strftime("%Y-%m-%d %H:%M")
                else:
                    last_str = "Never"
                
                # Color code based on coverage
                rec_count = coverage["total_recordings"]
                if rec_count >= 10:
                    count_style = "[green]"
                elif rec_count >= 5:
                    count_style = "[yellow]"
                else:
                    count_style = "[red]"
                
                table.add_row(
                    user,
                    f"{count_style}{rec_count}[/]",
                    duration_str,
                    str(coverage["total_events"]),
                    features_str,
                    last_str
                )
            
            self.console.print("\n")
            self.console.print(table)
        
        # Recent recordings
        if recordings:
            self.console.print("\n[bold]Recent Recordings:[/bold]")
            
            # Get last 5 recordings across all users
            all_recordings = []
            for user, user_recs in recordings.items():
                for rec in user_recs:
                    rec["user"] = user
                    all_recordings.append(rec)
            
            all_recordings.sort(key=lambda x: x.get("start_time", ""), reverse=True)
            recent = all_recordings[:5]
            
            recent_table = Table(box=box.SIMPLE)
            recent_table.add_column("Time", style="dim")
            recent_table.add_column("User", style="cyan")
            recent_table.add_column("Description")
            recent_table.add_column("Duration", justify="right")
            recent_table.add_column("Events", justify="right")
            
            for rec in recent:
                start_time = datetime.fromisoformat(rec["start_time"].replace('Z', '+00:00'))
                time_str = start_time.strftime("%H:%M")
                
                duration = rec.get("duration_seconds", 0)
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                duration_str = f"{minutes}:{seconds:02d}"
                
                recent_table.add_row(
                    time_str,
                    rec["user"],
                    rec.get("description", "No description"),
                    duration_str,
                    str(rec.get("events_count", 0))
                )
            
            self.console.print(recent_table)
        
        # Menu options
        self.console.print("\n[bold]Options:[/bold]")
        self.console.print("  [cyan]1[/cyan] - Start new recording")
        self.console.print("  [cyan]2[/cyan] - View recording details")
        self.console.print("  [cyan]3[/cyan] - Delete recordings")
        self.console.print("  [cyan]4[/cyan] - Export recordings")
        self.console.print("  [cyan]b[/cyan] - Back to project selection")
        self.console.print("  [cyan]q[/cyan] - Quit")
        
        choice = Prompt.ask("\n[bold]Choose option[/bold]", choices=["1", "2", "3", "4", "b", "q"])
        
        logger.info(f"User selected option: {choice}")
        return choice
    
    def check_duplicate(self, user: str, description: str) -> bool:
        """Check if similar recording already exists (user + description must be unique within project)"""
        logger.info(f"Checking for duplicate: user={user}, description={description} in project={self.project}")
        
        recordings = self._scan_recordings()
        
        if user in recordings:
            for rec in recordings[user]:
                if rec.get("description", "").lower() == description.lower():
                    logger.warning(f"Found duplicate recording: {rec['session_id']}")
                    
                    # Show warning
                    self.console.print(f"\n[yellow]⚠ Warning: Duplicate recording found![/yellow]")
                    self.console.print(f"  Project: {self.project}")
                    self.console.print(f"  User: {user}")
                    self.console.print(f"  Description: {description}")
                    self.console.print(f"  Recorded: {rec.get('start_time', 'Unknown')}")
                    
                    # Ask user to confirm
                    proceed = Confirm.ask("\nDo you want to create another recording anyway?")
                    return not proceed  # Return True if duplicate and user doesn't want to proceed
        
        return False
    
    def view_recording_details(self, session_id: str):
        """Display detailed information about a recording"""
        logger.info(f"Viewing details for session: {session_id}")
        
        # Find the recording
        recordings = self._scan_recordings()
        found = None
        
        for user, user_recs in recordings.items():
            for rec in user_recs:
                if session_id in rec.get("session_id", ""):
                    found = rec
                    found["user"] = user
                    break
            if found:
                break
        
        if not found:
            self.console.print(f"[red]Recording {session_id} not found![/red]")
            return
        
        # Display details
        self.console.print(Panel.fit(
            f"[bold]Recording Details: {found['session_id']}[/bold]",
            border_style="cyan"
        ))
        
        details_table = Table(box=box.SIMPLE, show_header=False)
        details_table.add_column("Field", style="cyan")
        details_table.add_column("Value")
        
        details_table.add_row("Project", self.project)
        details_table.add_row("User", found.get("user", "Unknown"))
        details_table.add_row("Description", found.get("description", "No description"))
        details_table.add_row("Start Time", found.get("start_time", "Unknown"))
        
        # Format duration in MM:SS
        duration = found.get("duration_seconds", 0)
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        duration_str = f"{minutes}:{seconds:02d}"
        details_table.add_row("Duration", duration_str)
        
        details_table.add_row("Total Events", str(found.get("events_count", 0)))
        details_table.add_row("HTTP Requests", str(found.get("requests_count", 0)))
        details_table.add_row("WebSocket Connections", str(found.get("websockets_count", 0)))
        details_table.add_row("Console Messages", str(found.get("console_count", 0)))
        details_table.add_row("Has Audio", "Yes" if found.get("audio_transcript") else "No")
        details_table.add_row("Session Path", found.get("path", "Unknown"))
        
        self.console.print(details_table)
        
        # Show transcript if available
        if found.get("audio_transcript"):
            self.console.print("\n[bold]Audio Transcript:[/bold]")
            self.console.print(Panel(
                found["audio_transcript"][:500] + "..." if len(found.get("audio_transcript", "")) > 500 else found.get("audio_transcript", ""),
                border_style="dim"
            ))
    
    def delete_recordings(self, user: Optional[str] = None):
        """Delete recordings for a user or all"""
        logger.info(f"Deleting recordings for user: {user or 'ALL'} in project: {self.project}")
        
        recordings = self._scan_recordings()
        
        if user and user not in recordings:
            self.console.print(f"[red]No recordings found for user: {user}[/red]")
            return
        
        # Confirm deletion
        if user:
            count = len(recordings[user])
            confirm_msg = f"Delete {count} recording(s) for user '{user}' in project '{self.project}'?"
        else:
            count = sum(len(v) for v in recordings.values())
            confirm_msg = f"Delete ALL {count} recording(s) in project '{self.project}'?"
        
        if not Confirm.ask(f"[red]{confirm_msg}[/red]"):
            self.console.print("[yellow]Deletion cancelled[/yellow]")
            return
        
        # Perform deletion
        try:
            import shutil
            
            if user:
                user_dir = self.recordings_dir / user
                if user_dir.exists():
                    shutil.rmtree(user_dir)
                    logger.info(f"Deleted recordings for user: {user}")
                    self.console.print(f"[green]Deleted {count} recording(s) for user '{user}'[/green]")
            else:
                for user_dir in self.recordings_dir.iterdir():
                    if user_dir.is_dir() and not user_dir.name.startswith('.'):
                        shutil.rmtree(user_dir)
                logger.info("Deleted all recordings")
                self.console.print(f"[green]Deleted all {count} recording(s)[/green]")
                
        except Exception as e:
            logger.error(f"Failed to delete recordings: {e}")
            self.console.print(f"[red]Error deleting recordings: {e}[/red]")
    
    def export_recordings(self, output_path: Optional[str] = None):
        """Export all recordings to a JSON file"""
        logger.info(f"Exporting recordings to {output_path or 'default'}")
        
        if not output_path:
            output_path = f"{self.project}_recordings_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        recordings = self._scan_recordings()
        
        if not recordings:
            self.console.print("[yellow]No recordings to export![/yellow]")
            return
        
        try:
            export_data = {
                "project": self.project,
                "export_time": datetime.now().isoformat(),
                "recordings": recordings
            }
            
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            total = sum(len(v) for v in recordings.values())
            logger.info(f"Exported {total} recordings to {output_path}")
            self.console.print(f"[green]Exported {total} recording(s) to {output_path}[/green]")
            
        except Exception as e:
            logger.error(f"Failed to export recordings: {e}")
            self.console.print(f"[red]Error exporting recordings: {e}[/red]")