"""Tests for config module."""

import pytest
from pathlib import Path
from unittest.mock import patch

from tonuino_organizer.config import Config


class TestConfig:
    """Tests for Config class."""
    
    def test_default_paths(self):
        """Test that default paths are set correctly."""
        config = Config()
        assert "tonuino" in str(config.input_path)
        assert "tonuino" in str(config.output_path)
        assert "input" in str(config.input_path)
        assert "output" in str(config.output_path)
    
    def test_custom_input_path(self, tmp_path):
        """Test custom input path."""
        custom_input = tmp_path / "custom_input"
        config = Config(input_path=str(custom_input))
        assert config.input_path == custom_input
    
    def test_custom_output_path(self, tmp_path):
        """Test custom output path."""
        custom_output = tmp_path / "custom_output"
        config = Config(output_path=str(custom_output))
        assert config.output_path == custom_output
    
    def test_custom_both_paths(self, tmp_path):
        """Test custom input and output paths."""
        custom_input = tmp_path / "input"
        custom_output = tmp_path / "output"
        config = Config(
            input_path=str(custom_input),
            output_path=str(custom_output)
        )
        assert config.input_path == custom_input
        assert config.output_path == custom_output
    
    def test_expands_tilde(self):
        """Test that ~ is expanded in paths."""
        config = Config(input_path="~/test_input")
        assert config.input_path == Path.home() / "test_input"
    
    def test_ensure_directories_creates_paths(self, tmp_path):
        """Test that ensure_directories creates paths."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        
        config = Config(
            input_path=str(input_dir),
            output_path=str(output_dir)
        )
        
        assert not input_dir.exists()
        assert not output_dir.exists()
        
        config.ensure_directories()
        
        assert input_dir.exists()
        assert output_dir.is_dir()
        assert output_dir.exists()
        assert output_dir.is_dir()
    
    def test_ensure_directories_creates_parents(self, tmp_path):
        """Test that ensure_directories creates parent directories."""
        nested_input = tmp_path / "deep" / "nested" / "input"
        
        config = Config(input_path=str(nested_input))
        config.ensure_directories()
        
        assert nested_input.exists()
        assert nested_input.is_dir()

