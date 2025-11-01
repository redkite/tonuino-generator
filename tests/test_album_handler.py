"""Tests for album_handler module."""

import pytest
from pathlib import Path

from tonuino_organizer.album_handler import process_static_album


class TestProcessStaticAlbum:
    """Tests for process_static_album function."""
    
    def test_process_static_album_finds_files(self, tmp_path):
        """Test that static album finds MP3 files."""
        # Create MP3 files
        (tmp_path / "song1.mp3").touch()
        (tmp_path / "song2.mp3").touch()
        
        mp3_files = process_static_album(tmp_path)
        
        assert len(mp3_files) == 2
        assert all(f.suffix.lower() == ".mp3" for f in mp3_files)
    
    def test_process_static_album_recursive(self, tmp_path):
        """Test that static album finds files recursively."""
        # Create MP3 files in subdirectories
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (tmp_path / "song1.mp3").touch()
        (subdir / "song2.mp3").touch()
        
        mp3_files = process_static_album(tmp_path)
        
        assert len(mp3_files) == 2
    
    def test_process_static_album_sorts_files(self, tmp_path):
        """Test that files are sorted naturally."""
        (tmp_path / "song10.mp3").touch()
        (tmp_path / "song2.mp3").touch()
        (tmp_path / "song1.mp3").touch()
        
        mp3_files = process_static_album(tmp_path)
        
        assert mp3_files[0].name == "song1.mp3"
        assert mp3_files[1].name == "song2.mp3"
        assert mp3_files[2].name == "song10.mp3"
    
    def test_process_static_album_no_files(self, tmp_path):
        """Test that empty folder returns empty list."""
        mp3_files = process_static_album(tmp_path)
        assert mp3_files == []
    
    def test_process_static_album_ignores_non_mp3(self, tmp_path):
        """Test that non-MP3 files are ignored."""
        (tmp_path / "song1.mp3").touch()
        (tmp_path / "song2.wav").touch()
        (tmp_path / "song3.txt").touch()
        
        mp3_files = process_static_album(tmp_path)
        
        assert len(mp3_files) == 1
        assert mp3_files[0].name == "song1.mp3"

