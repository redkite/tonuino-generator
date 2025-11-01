"""File organization logic: renaming and copying MP3 files."""

from pathlib import Path
from typing import List

import shutil
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.console import Console

from .utils import extract_two_digit_prefix, format_file_size

console = Console()


def organize_files(
    mp3_files: List[Path],
    folder_name: str,
    output_path: Path,
    overwrite: bool = True
) -> List[Path]:
    """
    Organize MP3 files into output directory with standardized naming.
    
    Args:
        mp3_files: List of MP3 file paths to organize (should be sorted)
        folder_name: Name of the source folder (used to extract prefix)
        output_path: Base output directory path
        overwrite: If True, overwrite existing files
        
    Returns:
        List of Path objects for the copied files
        
    Raises:
        ValueError: If folder name doesn't have a valid two-digit prefix
        ValueError: If there are more than 255 files
    """
    if len(mp3_files) > 255:
        raise ValueError(f"Too many MP3 files ({len(mp3_files)}). Maximum is 255.")
    
    # Extract two-digit prefix
    prefix = extract_two_digit_prefix(folder_name)
    
    # Create output folder
    output_folder = output_path / prefix
    output_folder.mkdir(parents=True, exist_ok=True)
    
    copied_files = []
    
    # Use rich progress bar for file operations
    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("•"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            f"Organizing {len(mp3_files)} files from {folder_name}",
            total=len(mp3_files)
        )
        
        for index, source_file in enumerate(mp3_files, start=1):
            # Generate new filename (001.mp3, 002.mp3, ..., 255.mp3)
            new_filename = f"{index:03d}.mp3"
            dest_file = output_folder / new_filename
            
            # Update progress description with current file
            progress.update(
                task,
                description=f"Copying {source_file.name} → {new_filename}",
                advance=0
            )
            
            # Copy file
            try:
                shutil.copy2(source_file, dest_file)
                copied_files.append(dest_file)
                
                # Show file size info
                file_size = source_file.stat().st_size
                console.print(
                    f"  [green]✓[/green] {source_file.name} → {new_filename} "
                    f"({format_file_size(file_size)})"
                )
            except Exception as e:
                console.print(
                    f"  [red]✗[/red] Error copying {source_file.name}: {e}",
                    style="red"
                )
                raise
            
            progress.advance(task)
    
    return copied_files

