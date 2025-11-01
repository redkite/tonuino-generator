"""Tests for utils module."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from tonuino_organizer.utils import (
    expand_path,
    is_mp3_file,
    natural_sort_key,
    sort_files_naturally,
    find_mp3_files,
    extract_two_digit_prefix,
    format_file_size,
)


class TestExpandPath:
    """Tests for expand_path function."""
    
    def test_expand_tilde(self, tmp_path):
        """Test that ~ is expanded correctly."""
        home = Path.home()
        result = expand_path("~/test")
        assert result == home / "test"
    
    def test_absolute_path(self, tmp_path):
        """Test that absolute paths work."""
        test_path = tmp_path / "test"
        result = expand_path(str(test_path))
        assert result == test_path
    
    def test_relative_path(self, tmp_path):
        """Test that relative paths work."""
        with patch('pathlib.Path.cwd', return_value=tmp_path):
            result = expand_path("relative")
            assert isinstance(result, Path)


class TestIsMp3File:
    """Tests for is_mp3_file function."""
    
    def test_valid_mp3_extension(self, tmp_path):
        """Test that .mp3 extension is recognized."""
        file_path = tmp_path / "test.mp3"
        file_path.touch()
        assert is_mp3_file(file_path) is True
    
    def test_case_insensitive_mp3(self, tmp_path):
        """Test that .MP3 extension is recognized."""
        file_path = tmp_path / "test.MP3"
        file_path.touch()
        assert is_mp3_file(file_path) is True
    
    def test_non_mp3_extension(self, tmp_path):
        """Test that non-MP3 files return False."""
        file_path = tmp_path / "test.wav"
        file_path.touch()
        assert is_mp3_file(file_path) is False
    
    def test_directory_returns_false(self, tmp_path):
        """Test that directories return False."""
        dir_path = tmp_path / "test_dir"
        dir_path.mkdir()
        assert is_mp3_file(dir_path) is False


class TestNaturalSortKey:
    """Tests for natural_sort_key function."""
    
    def test_basic_string(self):
        """Test basic string sorting key."""
        key = natural_sort_key("test")
        assert key == ["test"]
    
    def test_string_with_numbers(self):
        """Test sorting key with numbers."""
        key = natural_sort_key("file10.mp3")
        # The regex splits on all numbers, so "mp3" is split into ".mp", 3, ""
        assert key == ["file", 10, ".mp", 3, ""]
    
    def test_case_insensitive(self):
        """Test that sorting is case-insensitive."""
        key1 = natural_sort_key("FILE.mp3")
        key2 = natural_sort_key("file.mp3")
        assert key1[0] == key2[0]
    
    def test_multiple_numbers(self):
        """Test string with multiple numbers."""
        key = natural_sort_key("file10test20.mp3")
        # The regex splits on all numbers, so "mp3" is split into ".mp", 3, ""
        assert key == ["file", 10, "test", 20, ".mp", 3, ""]


class TestSortFilesNaturally:
    """Tests for sort_files_naturally function."""
    
    def test_sorts_files_naturally(self, tmp_path):
        """Test that files are sorted naturally."""
        files = [
            tmp_path / "file10.mp3",
            tmp_path / "file2.mp3",
            tmp_path / "file1.mp3",
        ]
        sorted_files = sort_files_naturally(files)
        assert sorted_files[0].name == "file1.mp3"
        assert sorted_files[1].name == "file2.mp3"
        assert sorted_files[2].name == "file10.mp3"


class TestFindMp3Files:
    """Tests for find_mp3_files function."""
    
    def test_finds_mp3_files_recursive(self, tmp_path):
        """Test finding MP3 files recursively."""
        # Create MP3 files
        (tmp_path / "file1.mp3").touch()
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file2.mp3").touch()
        
        # Create non-MP3 file
        (tmp_path / "file.wav").touch()
        
        mp3_files = find_mp3_files(tmp_path, recursive=True)
        assert len(mp3_files) == 2
        assert all(f.suffix.lower() == ".mp3" for f in mp3_files)
    
    def test_finds_mp3_files_non_recursive(self, tmp_path):
        """Test finding MP3 files non-recursively."""
        # Create MP3 files
        (tmp_path / "file1.mp3").touch()
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file2.mp3").touch()
        
        mp3_files = find_mp3_files(tmp_path, recursive=False)
        assert len(mp3_files) == 1
        assert mp3_files[0].name == "file1.mp3"
    
    def test_nonexistent_directory(self):
        """Test that nonexistent directory returns empty list."""
        mp3_files = find_mp3_files(Path("/nonexistent/path"), recursive=True)
        assert mp3_files == []
    
    def test_empty_directory(self, tmp_path):
        """Test that empty directory returns empty list."""
        mp3_files = find_mp3_files(tmp_path, recursive=True)
        assert mp3_files == []
    
    def test_sorts_results_naturally(self, tmp_path):
        """Test that results are sorted naturally."""
        (tmp_path / "file10.mp3").touch()
        (tmp_path / "file2.mp3").touch()
        (tmp_path / "file1.mp3").touch()
        
        mp3_files = find_mp3_files(tmp_path, recursive=True)
        assert mp3_files[0].name == "file1.mp3"
        assert mp3_files[1].name == "file2.mp3"
        assert mp3_files[2].name == "file10.mp3"


class TestExtractTwoDigitPrefix:
    """Tests for extract_two_digit_prefix function."""
    
    def test_valid_two_digit_prefix(self):
        """Test extracting valid two-digit prefix."""
        assert extract_two_digit_prefix("01_Album") == "01"
        assert extract_two_digit_prefix("15_Podcast") == "15"
        assert extract_two_digit_prefix("99_Test") == "99"
    
    def test_two_digit_at_start(self):
        """Test that prefix is extracted from start."""
        assert extract_two_digit_prefix("01_Album") == "01"
        assert extract_two_digit_prefix("15_Podcast") == "15"
    
    def test_invalid_prefix_raises_error(self):
        """Test that invalid prefix raises ValueError."""
        with pytest.raises(ValueError, match="does not start with a two-digit prefix"):
            extract_two_digit_prefix("Album")
        
        with pytest.raises(ValueError, match="does not start with a two-digit prefix"):
            extract_two_digit_prefix("1_Album")
        
        with pytest.raises(ValueError, match="does not start with a two-digit prefix"):
            extract_two_digit_prefix("001_Album")  # Three digits, not two
        
        with pytest.raises(ValueError, match="does not start with a two-digit prefix"):
            extract_two_digit_prefix("01Album")  # Missing underscore
        
        with pytest.raises(ValueError):
            extract_two_digit_prefix("")


class TestFormatFileSize:
    """Tests for format_file_size function."""
    
    def test_bytes(self):
        """Test formatting bytes."""
        assert format_file_size(512) == "512.0 B"
        assert format_file_size(0) == "0.0 B"
    
    def test_kilobytes(self):
        """Test formatting kilobytes."""
        size_kb = 1024 * 1.5
        result = format_file_size(int(size_kb))
        assert "KB" in result
    
    def test_megabytes(self):
        """Test formatting megabytes."""
        size_mb = 1024 * 1024 * 2.5
        result = format_file_size(int(size_mb))
        assert "MB" in result
    
    def test_gigabytes(self):
        """Test formatting gigabytes."""
        size_gb = 1024 * 1024 * 1024 * 1.5
        result = format_file_size(int(size_gb))
        assert "GB" in result

