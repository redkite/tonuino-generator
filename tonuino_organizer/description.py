"""Description file parser for album/podcast configuration."""

from pathlib import Path
from typing import Dict, Optional

import yaml


class DescriptionError(Exception):
    """Error reading or parsing description file."""
    pass


def load_description(folder_path: Path) -> Dict:
    """
    Load and parse description.yaml file from a folder.
    
    Args:
        folder_path: Path to the folder containing description.yaml
        
    Returns:
        Dictionary with description data (type, feed_url if applicable)
        
    Raises:
        DescriptionError: If description file is missing or invalid
    """
    description_file = folder_path / "description.yaml"
    
    if not description_file.exists():
        raise DescriptionError(f"Description file not found: {description_file}")
    
    try:
        with open(description_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise DescriptionError(f"Invalid YAML in description file: {e}")
    except Exception as e:
        raise DescriptionError(f"Error reading description file: {e}")
    
    if not isinstance(data, dict):
        raise DescriptionError("Description file must contain a YAML dictionary")
    
    # Validate required fields
    if 'type' not in data:
        raise DescriptionError("Description file must contain 'type' field")
    
    description_type = data['type']
    if description_type not in ['static', 'rss']:
        raise DescriptionError(f"Invalid type '{description_type}'. Must be 'static' or 'rss'")
    
    # Validate feed_url for RSS type
    if description_type == 'rss':
        if 'feed_url' not in data:
            raise DescriptionError("Description file with type 'rss' must contain 'feed_url' field")
        if not data['feed_url'] or not isinstance(data['feed_url'], str):
            raise DescriptionError("'feed_url' must be a non-empty string")
    
    # Validate min_duration if present (optional, must be positive number)
    if 'min_duration' in data:
        min_duration = data['min_duration']
        if not isinstance(min_duration, (int, float)):
            raise DescriptionError("'min_duration' must be a number")
        if min_duration <= 0:
            raise DescriptionError("'min_duration' must be a positive number")
    
    return data


def get_description_type(folder_path: Path) -> str:
    """
    Get the type from a description file.
    
    Args:
        folder_path: Path to the folder containing description.yaml
        
    Returns:
        Type string ('static' or 'rss')
    """
    data = load_description(folder_path)
    return data['type']


def get_feed_url(folder_path: Path) -> Optional[str]:
    """
    Get the feed URL from a description file.
    
    Args:
        folder_path: Path to the folder containing description.yaml
        
    Returns:
        Feed URL string or None if not RSS type
    """
    data = load_description(folder_path)
    return data.get('feed_url')


def get_min_duration(folder_path: Path, default: float = 60.0) -> float:
    """
    Get the minimum duration in seconds from a description file.
    
    Args:
        folder_path: Path to the folder containing description.yaml
        default: Default minimum duration in seconds if not specified (default: 60.0)
        
    Returns:
        Minimum duration in seconds (from description.yaml or default)
    """
    data = load_description(folder_path)
    return data.get('min_duration', default)

