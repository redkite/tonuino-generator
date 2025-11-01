"""Handler for RSS feed podcast processing and downloading."""

import hashlib
import re
from pathlib import Path
from typing import List, Set, Dict, Optional
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
        self.url_mapping_file = folder_path / ".url_mapping"
        self.downloaded_urls: Set[str] = self._load_downloaded_urls()
        self.rejected_urls: Set[str] = self._load_rejected_urls()
        self.url_to_number: Dict[str, int] = self._load_url_mapping()
        self.local_files_by_number: Dict[int, Path] = self._scan_local_files()
    
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
    
    def _load_url_mapping(self) -> Dict[str, int]:
        """
        Load URL to number mapping from file.
        
        Format: URL|NUMBER
        
        Returns:
            Dictionary mapping URL to number
        """
        if not self.url_mapping_file.exists():
            return {}
        
        try:
            url_to_number = {}
            with open(self.url_mapping_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if '|' in line:
                        url, number_str = line.split('|', 1)
                        try:
                            url_to_number[url] = int(number_str)
                        except ValueError:
                            continue
            return url_to_number
        except Exception as e:
            console.print(f"[yellow]Warning: Could not read URL mapping: {e}[/yellow]")
            return {}
    
    def _save_url_mapping(self, url: str, number: int):
        """Save URL to number mapping."""
        try:
            with open(self.url_mapping_file, 'a', encoding='utf-8') as f:
                f.write(f"{url}|{number}\n")
            self.url_to_number[url] = number
        except Exception as e:
            console.print(f"[yellow]Warning: Could not save URL mapping: {e}[/yellow]")
    
    def _scan_local_files(self) -> Dict[int, Path]:
        """
        Scan local files and extract their three-digit prefixes.
        
        Returns:
            Dictionary mapping number to file path
        """
        local_files = {}
        mp3_files = find_mp3_files(self.folder_path, recursive=True)
        
        for file_path in mp3_files:
            # Check if filename starts with three digits followed by underscore
            match = re.match(r'^(\d{3})_', file_path.name)
            if match:
                number = int(match.group(1))
                local_files[number] = file_path
        
        return local_files
    
    def _match_local_file_to_url(self, url: str) -> Optional[int]:
        """
        Try to match a local file to a URL by checking the URL mapping.
        
        Args:
            url: URL to match
            
        Returns:
            Number if URL matches a local file, None otherwise
        """
        if url in self.url_to_number:
            number = self.url_to_number[url]
            if number in self.local_files_by_number:
                return number
        return None
    
    
    def _get_numbered_filename(self, url: str, episode_title: str, number: int) -> str:
        """
        Generate a numbered filename.
        
        Args:
            url: Download URL
            episode_title: Episode title
            number: Three-digit number prefix
            
        Returns:
            Filename with three-digit prefix (e.g., "001_Episode_Title.mp3")
        """
        # Get base filename
        base_filename = self._get_filename_from_url(url, episode_title)
        
        # Remove any existing three-digit prefix
        base_filename = re.sub(r'^\d{3}_', '', base_filename)
        
        # Add three-digit prefix
        return f"{number:03d}_{base_filename}"
    
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
        
        # Reverse feed entries for chronological order (oldest first)
        # Feed entries are usually newest first, so reverse to get chronological
        feed_entries = list(reversed(feed.entries))
        
        # Build URL to entry mapping for lookup
        url_to_entry = {}
        for entry in feed_entries:
            mp3_url = None
            if hasattr(entry, 'enclosures'):
                for enclosure in entry.enclosures:
                    if enclosure.get('type', '').startswith('audio/'):
                        mp3_url = enclosure.get('href')
                        break
            if not mp3_url and hasattr(entry, 'links'):
                for link in entry.links:
                    if link.get('type', '').startswith('audio/'):
                        mp3_url = link.get('href')
                        break
            if mp3_url:
                url_to_entry[mp3_url] = entry
        
        # Build set of URLs in current feed
        feed_urls = set(url_to_entry.keys())
        
        # Find numbers used by local files NOT in feed (to preserve their numbering)
        # These are files that exist locally but their URLs are no longer in the feed
        numbers_reserved_by_orphaned_files = set()
        for number, file_path in self.local_files_by_number.items():
            # Check if this number maps to a URL not in the current feed
            url_for_number = None
            for url, num in self.url_to_number.items():
                if num == number:
                    url_for_number = url
                    break
            
            if url_for_number is None or url_for_number not in feed_urls:
                # This number is used by a file not in feed (or unmapped), reserve it
                # to keep numbering consistent - these files keep their numbers
                numbers_reserved_by_orphaned_files.add(number)
        
        downloaded_files = []
        new_episodes = 0
        current_number = 1
        
        # Process entries in chronological order (oldest first)
        for entry in feed_entries:
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
            
            # Skip if already rejected (too short)
            if mp3_url in self.rejected_urls:
                continue
            
            episode_title = entry.get('title', 'Unknown Episode')
            
            # Check if URL matches an existing local file
            assigned_number = self._match_local_file_to_url(mp3_url)
            
            if assigned_number is not None:
                # File already exists with this number, skip downloading
                existing_file = self.local_files_by_number[assigned_number]
                console.print(f"  [dim]Skipping {episode_title} (already exists: {existing_file.name})[/dim]")
                # Update current_number to be after this existing file
                if assigned_number >= current_number:
                    current_number = assigned_number + 1
                continue
            
            # Assign number for new download chronologically
            # Skip numbers reserved by files not in feed
            while current_number in numbers_reserved_by_orphaned_files:
                current_number += 1
                if current_number > 999:
                    console.print(f"  [red]Cannot assign number > 999 for {episode_title}, skipping[/red]")
                    break
            
            if current_number > 999:
                continue
            
            assigned_number = current_number
            current_number += 1  # Prepare for next iteration
            
            # Generate numbered filename
            filename = self._get_numbered_filename(mp3_url, episode_title, assigned_number)
            dest_file = self.folder_path / filename
            
            # Ensure file doesn't exist (shouldn't happen, but safety check)
            if dest_file.exists():
                console.print(f"  [yellow]Warning: File {dest_file.name} already exists, skipping[/yellow]")
                continue
            
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
                self._save_url_mapping(mp3_url, assigned_number)
                # Update local files tracking
                self.local_files_by_number[assigned_number] = dest_file
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

