"""Utility functions for file operations and validation."""

import re
from pathlib import Path
from typing import List


def expand_path(path: str) -> Path:
    """Expand user home directory (~) and return Path object."""
    return Path(path).expanduser()


def is_mp3_file(file_path: Path) -> bool:
    """Check if a file is an MP3 file."""
    return file_path.is_file() and file_path.suffix.lower() == ".mp3"


def natural_sort_key(text: str) -> List:
    """
    Generate a sort key for natural (alphanumeric) sorting.
    
    Splits text into alternating sequences of numbers and non-numbers,
    converting numbers to integers for proper numeric sorting.
    
    Example:
        "file10.mp3" -> ['file', 10, '.mp3']
        "file2.mp3" -> ['file', 2, '.mp3']
    """
    def convert(text_part):
        return int(text_part) if text_part.isdigit() else text_part.lower()
    
    return [convert(c) for c in re.split(r'(\d+)', text)]


def sort_files_naturally(files: List[Path]) -> List[Path]:
    """
    Sort a list of file paths naturally (alphanumerically).
    
    Args:
        files: List of Path objects to sort
        
    Returns:
        List of Path objects sorted naturally
    """
    return sorted(files, key=lambda f: natural_sort_key(f.name))


def find_mp3_files(directory: Path, recursive: bool = True) -> List[Path]:
    """
    Find all MP3 files in a directory.
    
    Args:
        directory: Directory to search
        recursive: If True, search recursively in subdirectories
        
    Returns:
        List of Path objects for MP3 files, sorted naturally
    """
    if not directory.exists() or not directory.is_dir():
        return []
    
    mp3_files = []
    
    if recursive:
        for file_path in directory.rglob("*.mp3"):
            if is_mp3_file(file_path):
                mp3_files.append(file_path)
    else:
        for file_path in directory.glob("*.mp3"):
            if is_mp3_file(file_path):
                mp3_files.append(file_path)
    
    return sort_files_naturally(mp3_files)


def extract_two_digit_prefix(folder_name: str) -> str:
    """
    Extract the two-digit prefix from a folder name.
    
    Args:
        folder_name: Name of the folder (e.g., "01_MyAlbum" or "15_Podcast")
        
    Returns:
        Two-digit prefix string (e.g., "01" or "15")
        
    Raises:
        ValueError: If folder name doesn't start with two digits
    """
    match = re.match(r'^(\d{2})', folder_name)
    if not match:
        raise ValueError(f"Folder name '{folder_name}' does not start with a two-digit prefix")
    return match.group(1)


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Human-readable size string (e.g., "1.5 MB", "256 KB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

