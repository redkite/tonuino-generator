"""Configuration management for default paths."""

from pathlib import Path
from typing import Optional

from .utils import expand_path


class Config:
    """Configuration for tonuino organizer."""
    
    DEFAULT_INPUT_PATH = "~/data/tonuino/input"
    DEFAULT_OUTPUT_PATH = "~/data/tonuino/output"
    
    def __init__(
        self,
        input_path: Optional[str] = None,
        output_path: Optional[str] = None
    ):
        """
        Initialize configuration.
        
        Args:
            input_path: Input directory path (defaults to ~/data/tonuino/input)
            output_path: Output directory path (defaults to ~/data/tonuino/output)
        """
        self.input_path = expand_path(input_path or self.DEFAULT_INPUT_PATH)
        self.output_path = expand_path(output_path or self.DEFAULT_OUTPUT_PATH)
    
    def ensure_directories(self):
        """Create input and output directories if they don't exist."""
        self.input_path.mkdir(parents=True, exist_ok=True)
        self.output_path.mkdir(parents=True, exist_ok=True)

