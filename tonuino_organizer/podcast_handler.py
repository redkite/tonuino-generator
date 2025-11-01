"""Handler for RSS feed podcast processing and downloading."""

import hashlib
from pathlib import Path
from typing import List, Set
from urllib.parse import urlparse

import feedparser
import requests
from mutagen.mp3 import MP3
from mutagen import MutagenError
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, DownloadColumn, TransferSpeedColumn

from .utils import find_mp3_files, format_file_size

console = Console()

# Default minimum duration in seconds (10 minutes)
DEFAULT_MIN_DURATION_SECONDS = 600


class PodcastHandler:
    """Handler for RSS feed podcasts."""
    
    def __init__(self, folder_path: Path, min_duration: float = DEFAULT_MIN_DURATION_SECONDS):
        """
        Initialize podcast handler.
        
        Args:
            folder_path: Path to the podcast folder
            min_duration: Minimum duration in seconds for keeping files (default: 60.0)
        """
        self.folder_path = folder_path
        self.min_duration = min_duration
        self.downloaded_files_file = folder_path / ".downloaded_files"
        self.rejected_files_file = folder_path / ".rejected_files"
        self.downloaded_urls: Set[str] = self._load_downloaded_urls()
        self.rejected_urls: Set[str] = self._load_rejected_urls()
    
    def _load_downloaded_urls(self) -> Set[str]:
        """Load set of already downloaded file URLs."""
        if not self.downloaded_files_file.exists():
            return set()
        
        try:
            with open(self.downloaded_files_file, 'r', encoding='utf-8') as f:
                return {line.strip() for line in f if line.strip()}
        except Exception as e:
            console.print(f"[yellow]Warning: Could not read downloaded files list: {e}[/yellow]")
            return set()
    
    def _load_rejected_urls(self) -> Set[str]:
        """Load set of rejected (too short) file URLs."""
        if not self.rejected_files_file.exists():
            return set()
        
        try:
            with open(self.rejected_files_file, 'r', encoding='utf-8') as f:
                return {line.strip() for line in f if line.strip()}
        except Exception as e:
            console.print(f"[yellow]Warning: Could not read rejected files list: {e}[/yellow]")
            return set()
    
    def _save_downloaded_url(self, url: str):
        """Save a downloaded URL to the tracking file."""
        try:
            with open(self.downloaded_files_file, 'a', encoding='utf-8') as f:
                f.write(f"{url}\n")
            self.downloaded_urls.add(url)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not save downloaded URL: {e}[/yellow]")
    
    def _save_rejected_url(self, url: str):
        """Save a rejected URL to the tracking file."""
        try:
            with open(self.rejected_files_file, 'a', encoding='utf-8') as f:
                f.write(f"{url}\n")
            self.rejected_urls.add(url)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not save rejected URL: {e}[/yellow]")
    
    def _get_mp3_duration(self, file_path: Path) -> float:
        """
        Get the duration of an MP3 file in seconds.
        
        Args:
            file_path: Path to the MP3 file
            
        Returns:
            Duration in seconds, or 0.0 if unable to read
        """
        try:
            audio = MP3(file_path)
            return audio.info.length
        except (MutagenError, Exception) as e:
            console.print(f"[yellow]Warning: Could not read duration of {file_path.name}: {e}[/yellow]")
            return 0.0
    
    def _is_file_too_short(self, file_path: Path) -> bool:
        """
        Check if an MP3 file is shorter than the minimum duration.
        
        Args:
            file_path: Path to the MP3 file
            
        Returns:
            True if file is shorter than minimum duration
        """
        duration = self._get_mp3_duration(file_path)
        return duration > 0 and duration < self.min_duration
    
    def _get_filename_from_url(self, url: str, episode_title: str = None) -> str:
        """
        Generate a filename from a URL.
        
        Args:
            url: Download URL
            episode_title: Optional episode title for better naming
            
        Returns:
            Filename string
        """
        # Try to get filename from URL
        parsed = urlparse(url)
        filename = Path(parsed.path).name
        
        # If no extension or not .mp3, use episode title
        if not filename.endswith('.mp3') or not filename:
            if episode_title:
                # Clean episode title for filename
                safe_title = "".join(c for c in episode_title if c.isalnum() or c in (' ', '-', '_')).strip()
                safe_title = safe_title.replace(' ', '_')
                filename = f"{safe_title}.mp3"
            else:
                # Fallback: use hash of URL
                url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                filename = f"episode_{url_hash}.mp3"
        
        # Ensure .mp3 extension
        if not filename.endswith('.mp3'):
            filename += '.mp3'
        
        return filename
    
    def download_episodes(self, feed_url: str) -> List[Path]:
        """
        Download new episodes from RSS feed.
        
        Args:
            feed_url: URL of the RSS feed
            
        Returns:
            List of Path objects for downloaded files
        """
        console.print(f"[cyan]Fetching RSS feed:[/cyan] {feed_url}")
        
        try:
            feed = feedparser.parse(feed_url)
        except Exception as e:
            console.print(f"[red]Error parsing RSS feed: {e}[/red]")
            return []
        
        if feed.bozo:
            console.print(f"[yellow]Warning: RSS feed parsing had issues: {feed.bozo_exception}[/yellow]")
        
        if not feed.entries:
            console.print("[yellow]No entries found in RSS feed[/yellow]")
            return []
        
        console.print(f"  Found {len(feed.entries)} episode(s) in feed")
        
        downloaded_files = []
        new_episodes = 0
        
        # Process entries (usually newest first)
        for entry in feed.entries:
            # Find MP3 enclosure
            mp3_url = None
            if hasattr(entry, 'enclosures'):
                for enclosure in entry.enclosures:
                    if enclosure.get('type', '').startswith('audio/'):
                        mp3_url = enclosure.get('href')
                        break
            
            # Fallback: check links
            if not mp3_url and hasattr(entry, 'links'):
                for link in entry.links:
                    if link.get('type', '').startswith('audio/'):
                        mp3_url = link.get('href')
                        break
            
            if not mp3_url:
                continue
            
            # Skip if already downloaded or rejected (too short)
            if mp3_url in self.downloaded_urls or mp3_url in self.rejected_urls:
                continue
            
            # Download the episode
            episode_title = entry.get('title', 'Unknown Episode')
            filename = self._get_filename_from_url(mp3_url, episode_title)
            dest_file = self.folder_path / filename
            
            # Handle filename conflicts
            counter = 1
            original_dest = dest_file
            while dest_file.exists():
                stem = original_dest.stem
                dest_file = self.folder_path / f"{stem}_{counter}.mp3"
                counter += 1
            
            console.print(f"\n[yellow]Downloading:[/yellow] {episode_title}")
            console.print(f"  URL: {mp3_url}")
            console.print(f"  Saving as: {dest_file.name}")
            
            try:
                response = requests.get(mp3_url, stream=True, timeout=30)
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                
                # Download with progress bar
                with open(dest_file, 'wb') as f:
                    with Progress(
                        TextColumn("[progress.description]{task.description}"),
                        BarColumn(),
                        DownloadColumn(),
                        TextColumn("•"),
                        TransferSpeedColumn(),
                        TextColumn("•"),
                        TimeRemainingColumn(),
                        console=console,
                    ) as progress:
                        task = progress.add_task(
                            f"Downloading {dest_file.name}",
                            total=total_size if total_size > 0 else None
                        )
                        
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                if total_size > 0:
                                    progress.update(task, advance=len(chunk))
                
                # Check duration after download
                duration = self._get_mp3_duration(dest_file)
                
                if duration > 0 and duration < self.min_duration:
                    # File is too short, delete it and mark as rejected
                    console.print(
                        f"  [yellow]⚠ File too short ({duration:.1f}s < {self.min_duration:.1f}s), "
                        f"discarding:[/yellow] {dest_file.name}"
                    )
                    dest_file.unlink()
                    self._save_rejected_url(mp3_url)
                    continue
                
                console.print(
                    f"  [green]✓ Downloaded:[/green] {dest_file.name} "
                    f"({format_file_size(dest_file.stat().st_size)}, {duration:.1f}s)"
                )
                downloaded_files.append(dest_file)
                self._save_downloaded_url(mp3_url)
                new_episodes += 1
                
            except Exception as e:
                console.print(f"  [red]✗ Error downloading {episode_title}: {e}[/red]")
                # Clean up partial file
                if dest_file.exists():
                    dest_file.unlink()
                continue
        
        if new_episodes > 0:
            console.print(f"\n[green]Downloaded {new_episodes} new episode(s)[/green]")
        else:
            console.print("\n[yellow]No new episodes to download[/yellow]")
        
        return downloaded_files
    
    def get_local_files(self) -> List[Path]:
        """
        Get all local MP3 files in the podcast folder.
        Removes any files that are too short.
        
        Returns:
            List of MP3 file paths, sorted naturally
        """
        mp3_files = find_mp3_files(self.folder_path, recursive=True)
        
        # Check existing files and remove any that are too short
        files_to_remove = []
        for file_path in mp3_files:
            if self._is_file_too_short(file_path):
                duration = self._get_mp3_duration(file_path)
                console.print(
                    f"[yellow]Removing too-short file ({duration:.1f}s):[/yellow] {file_path.name}"
                )
                file_path.unlink()
                files_to_remove.append(file_path)
        
        # Return files that are not too short
        return [f for f in mp3_files if f not in files_to_remove]


def process_podcast(
    folder_path: Path,
    feed_url: str,
    update: bool = False,
    min_duration: float = DEFAULT_MIN_DURATION_SECONDS
) -> List[Path]:
    """
    Process a podcast folder: optionally update from RSS feed, then return all MP3 files.
    
    Args:
        folder_path: Path to the podcast folder
        feed_url: URL of the RSS feed
        update: If True, download new episodes from feed
        min_duration: Minimum duration in seconds for keeping files (default: 60.0)
        
    Returns:
        List of MP3 file paths, sorted naturally
    """
    console.print(f"[cyan]Processing podcast:[/cyan] {folder_path.name}")
    if min_duration != DEFAULT_MIN_DURATION_SECONDS:
        console.print(f"  [dim]Minimum duration: {min_duration:.1f} seconds[/dim]")
    
    handler = PodcastHandler(folder_path, min_duration=min_duration)
    
    if update:
        handler.download_episodes(feed_url)
    
    mp3_files = handler.get_local_files()
    
    if not mp3_files:
        console.print(f"  [yellow]No MP3 files found in {folder_path.name}[/yellow]")
        return []
    
    console.print(f"  Found {len(mp3_files)} MP3 file(s)")
    return mp3_files

