"""Handler for static album processing."""

from pathlib import Path
from typing import List

from rich.console import Console

from .utils import find_mp3_files

console = Console()


def process_static_album(folder_path: Path) -> List[Path]:
    """
    Process a static album folder: find and return all MP3 files.
    
    Args:
        folder_path: Path to the album folder
        
    Returns:
        List of MP3 file paths, sorted naturally
    """
    console.print(f"[cyan]Processing static album:[/cyan] {folder_path.name}")
    
    mp3_files = find_mp3_files(folder_path, recursive=True)
    
    if not mp3_files:
        console.print(f"  [yellow]No MP3 files found in {folder_path.name}[/yellow]")
        return []
    
    console.print(f"  Found {len(mp3_files)} MP3 file(s)")
    return mp3_files

