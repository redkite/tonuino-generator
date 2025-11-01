"""Command-line interface for tonuino organizer."""

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config import Config
from .description import DescriptionError, get_description_type, get_feed_url, get_min_duration
from .album_handler import process_static_album
from .podcast_handler import process_podcast
from .file_organizer import organize_files
from .utils import extract_two_digit_prefix

console = Console()


def find_album_folders(input_path: Path):
    """
    Find all folders with two-digit prefixes in the input directory.
    
    Args:
        input_path: Input directory path
        
    Yields:
        Path objects for valid album/podcast folders
    """
    if not input_path.exists():
        console.print(f"[red]Input directory does not exist: {input_path}[/red]")
        return
    
    for item in input_path.iterdir():
        if item.is_dir():
            try:
                # Validate two-digit prefix
                extract_two_digit_prefix(item.name)
                yield item
            except ValueError:
                # Skip folders without valid prefix
                continue


@click.command()
@click.option(
    '--input',
    '-i',
    type=str,
    default=None,
    help=f'Input directory path (default: {Config.DEFAULT_INPUT_PATH})'
)
@click.option(
    '--output',
    '-o',
    type=str,
    default=None,
    help=f'Output directory path (default: {Config.DEFAULT_OUTPUT_PATH})'
)
@click.option(
    '--update',
    '-u',
    is_flag=True,
    help='Update RSS feeds and download new episodes'
)
def main(input: str, output: str, update: bool):
    """
    Organize MP3 files from input folders into standardized output structure.
    
    Processes albums/podcasts in folders that start with exactly two digits
    followed by underscore (e.g., 01_Album, 15_Podcast).
    Each folder should contain a description.yaml file.
    """
    # Initialize configuration
    config = Config(input_path=input, output_path=output)
    config.ensure_directories()
    
    console.print("\n[bold cyan]Tonuino Organizer[/bold cyan]\n")
    console.print(f"Input:  {config.input_path}")
    console.print(f"Output: {config.output_path}")
    if update:
        console.print("[yellow]Update mode: RSS feeds will be checked for new episodes[/yellow]")
    console.print()
    
    # Find all album/podcast folders
    folders = list(find_album_folders(config.input_path))
    
    if not folders:
        console.print("[yellow]No valid album/podcast folders found (folders must start with two digits followed by underscore, e.g., 01_Album)[/yellow]")
        return
    
    console.print(f"Found {len(folders)} album/podcast folder(s)\n")
    
    # Statistics
    stats = {
        'processed': 0,
        'errors': 0,
        'files_copied': 0
    }
    
    # Process each folder
    for folder_path in folders:
        folder_name = folder_path.name
        
        try:
            # Extract prefix for display
            prefix = extract_two_digit_prefix(folder_name)
            
            # Read description file
            try:
                description_type = get_description_type(folder_path)
            except DescriptionError as e:
                console.print(f"\n[red]Error reading description for {folder_name}: {e}[/red]")
                stats['errors'] += 1
                continue
            
            console.print(f"\n{'='*60}")
            console.print(f"[bold]Folder:[/bold] {folder_name} (Type: {description_type})")
            console.print(f"{'='*60}")
            
            # Process based on type
            if description_type == 'static':
                mp3_files = process_static_album(folder_path)
            elif description_type == 'rss':
                feed_url = get_feed_url(folder_path)
                min_duration = get_min_duration(folder_path)
                mp3_files = process_podcast(folder_path, feed_url, update=update, min_duration=min_duration)
            else:
                console.print(f"[red]Unknown type: {description_type}[/red]")
                stats['errors'] += 1
                continue
            
            if not mp3_files:
                console.print(f"[yellow]No MP3 files to organize for {folder_name}[/yellow]")
                continue
            
            # Organize files
            try:
                copied_files = organize_files(
                    mp3_files,
                    folder_name,
                    config.output_path,
                    overwrite=True
                )
                stats['files_copied'] += len(copied_files)
                stats['processed'] += 1
                console.print(f"[green]✓ Successfully organized {len(copied_files)} file(s) from {folder_name}[/green]")
            except Exception as e:
                console.print(f"[red]✗ Error organizing files from {folder_name}: {e}[/red]")
                stats['errors'] += 1
                continue
        
        except Exception as e:
            console.print(f"\n[red]Unexpected error processing {folder_name}: {e}[/red]")
            stats['errors'] += 1
            continue
    
    # Print summary
    console.print("\n" + "="*60)
    console.print("[bold]Summary[/bold]")
    console.print("="*60)
    
    summary_table = Table(show_header=False, box=None, padding=(0, 2))
    summary_table.add_row("[green]Successfully processed:[/green]", str(stats['processed']))
    summary_table.add_row("[green]Files copied:[/green]", str(stats['files_copied']))
    if stats['errors'] > 0:
        summary_table.add_row("[red]Errors:[/red]", str(stats['errors']))
    
    console.print(summary_table)
    console.print()


if __name__ == '__main__':
    main()

