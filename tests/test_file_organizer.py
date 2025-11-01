"""Tests for file_organizer module."""

import pytest
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from tonuino_organizer.file_organizer import organize_files
from tonuino_organizer.utils import extract_two_digit_prefix


class TestOrganizeFiles:
    """Tests for organize_files function."""
    
    def test_organize_files_basic(self, tmp_path):
        """Test basic file organization."""
        # Create input files
        input_dir = tmp_path / "input" / "01_Album"
        input_dir.mkdir(parents=True)
        
        file1 = input_dir / "song1.mp3"
        file2 = input_dir / "song2.mp3"
        file1.write_bytes(b"fake mp3 content 1")
        file2.write_bytes(b"fake mp3 content 2")
        
        # Create output directory
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        mp3_files = [file1, file2]
        copied_files = organize_files(
            mp3_files,
            "01_Album",
            output_dir,
            overwrite=True
        )
        
        # Check output structure
        assert len(copied_files) == 2
        output_folder = output_dir / "01"
        assert output_folder.exists()
        assert (output_folder / "001.mp3").exists()
        assert (output_folder / "002.mp3").exists()
    
    def test_organize_files_extracts_prefix(self, tmp_path):
        """Test that two-digit prefix is extracted correctly."""
        input_dir = tmp_path / "input" / "15_Podcast"
        input_dir.mkdir(parents=True)
        
        file1 = input_dir / "episode1.mp3"
        file1.write_bytes(b"fake content")
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        copied_files = organize_files(
            [file1],
            "15_Podcast",
            output_dir
        )
        
        # Check that output is in folder "15"
        output_folder = output_dir / "15"
        assert output_folder.exists()
        assert (output_folder / "001.mp3").exists()
    
    def test_organize_files_renames_correctly(self, tmp_path):
        """Test that files are renamed to 001, 002, etc."""
        input_dir = tmp_path / "input" / "01_Album"
        input_dir.mkdir(parents=True)
        
        files = []
        for i in range(5):
            file_path = input_dir / f"song{i}.mp3"
            file_path.write_bytes(b"content")
            files.append(file_path)
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        copied_files = organize_files(files, "01_Album", output_dir)
        
        output_folder = output_dir / "01"
        for i in range(1, 6):
            expected_name = f"{i:03d}.mp3"
            assert (output_folder / expected_name).exists()
    
    def test_organize_files_too_many_files(self, tmp_path):
        """Test that more than 255 files raises error."""
        input_dir = tmp_path / "input" / "01_Album"
        input_dir.mkdir(parents=True)
        
        files = []
        for i in range(256):
            file_path = input_dir / f"song{i}.mp3"
            file_path.write_bytes(b"content")
            files.append(file_path)
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        with pytest.raises(ValueError, match="Too many MP3 files"):
            organize_files(files, "01_Album", output_dir)
    
    def test_organize_files_invalid_prefix(self, tmp_path):
        """Test that invalid prefix raises error."""
        input_dir = tmp_path / "input" / "Album"
        input_dir.mkdir(parents=True)
        
        file1 = input_dir / "song1.mp3"
        file1.write_bytes(b"content")
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        with pytest.raises(ValueError, match="does not start with a two-digit prefix"):
            organize_files([file1], "Album", output_dir)
    
    def test_organize_files_overwrites_existing(self, tmp_path):
        """Test that existing files are overwritten when overwrite=True."""
        input_dir = tmp_path / "input" / "01_Album"
        input_dir.mkdir(parents=True)
        
        file1 = input_dir / "song1.mp3"
        file1.write_bytes(b"new content")
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        output_folder = output_dir / "01"
        output_folder.mkdir()
        
        # Create existing file
        existing_file = output_folder / "001.mp3"
        existing_file.write_bytes(b"old content")
        
        organize_files([file1], "01_Album", output_dir, overwrite=True)
        
        # Check that file was overwritten
        assert existing_file.read_bytes() == b"new content"
    
    def test_organize_files_creates_output_directory(self, tmp_path):
        """Test that output directory is created if it doesn't exist."""
        input_dir = tmp_path / "input" / "01_Album"
        input_dir.mkdir(parents=True)
        
        file1 = input_dir / "song1.mp3"
        file1.write_bytes(b"content")
        
        output_dir = tmp_path / "output"
        
        # Don't create output_dir - function should create it
        organize_files([file1], "01_Album", output_dir)
        
        assert output_dir.exists()
        assert (output_dir / "01" / "001.mp3").exists()

