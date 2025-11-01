"""Tests for podcast_handler module."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
from io import BytesIO

from tonuino_organizer.podcast_handler import PodcastHandler, process_podcast, DEFAULT_MIN_DURATION_SECONDS


class TestPodcastHandler:
    """Tests for PodcastHandler class."""
    
    def test_init(self, tmp_path):
        """Test PodcastHandler initialization."""
        handler = PodcastHandler(tmp_path)
        
        assert handler.folder_path == tmp_path
        assert handler.min_duration == DEFAULT_MIN_DURATION_SECONDS
        assert handler.downloaded_urls == set()
        assert handler.rejected_urls == set()
    
    def test_init_custom_min_duration(self, tmp_path):
        """Test PodcastHandler with custom min_duration."""
        handler = PodcastHandler(tmp_path, min_duration=120.0)
        
        assert handler.min_duration == 120.0
    
    def test_load_downloaded_urls(self, tmp_path):
        """Test loading downloaded URLs from file."""
        downloaded_file = tmp_path / ".downloaded_files"
        downloaded_file.write_text(
            "https://example.com/ep1.mp3\n"
            "https://example.com/ep2.mp3\n"
        )
        
        handler = PodcastHandler(tmp_path)
        assert len(handler.downloaded_urls) == 2
        assert "https://example.com/ep1.mp3" in handler.downloaded_urls
    
    def test_load_rejected_urls(self, tmp_path):
        """Test loading rejected URLs from file."""
        rejected_file = tmp_path / ".rejected_files"
        rejected_file.write_text(
            "https://example.com/short1.mp3\n"
            "https://example.com/short2.mp3\n"
        )
        
        handler = PodcastHandler(tmp_path)
        assert len(handler.rejected_urls) == 2
        assert "https://example.com/short1.mp3" in handler.rejected_urls
    
    def test_save_downloaded_url(self, tmp_path):
        """Test saving downloaded URL."""
        handler = PodcastHandler(tmp_path)
        handler._save_downloaded_url("https://example.com/ep1.mp3")
        
        assert "https://example.com/ep1.mp3" in handler.downloaded_urls
        downloaded_file = tmp_path / ".downloaded_files"
        assert downloaded_file.exists()
        assert "https://example.com/ep1.mp3" in downloaded_file.read_text()
    
    def test_save_rejected_url(self, tmp_path):
        """Test saving rejected URL."""
        handler = PodcastHandler(tmp_path)
        handler._save_rejected_url("https://example.com/short.mp3")
        
        assert "https://example.com/short.mp3" in handler.rejected_urls
        rejected_file = tmp_path / ".rejected_files"
        assert rejected_file.exists()
        assert "https://example.com/short.mp3" in rejected_file.read_text()
    
    @patch('tonuino_organizer.podcast_handler.MP3')
    def test_get_mp3_duration(self, mock_mp3_class, tmp_path):
        """Test getting MP3 duration."""
        # Create mock audio object
        mock_audio = MagicMock()
        mock_audio.info.length = 120.5
        mock_mp3_class.return_value = mock_audio
        
        file_path = tmp_path / "test.mp3"
        file_path.touch()
        
        handler = PodcastHandler(tmp_path)
        duration = handler._get_mp3_duration(file_path)
        
        assert duration == 120.5
        mock_mp3_class.assert_called_once_with(file_path)
    
    @patch('tonuino_organizer.podcast_handler.MP3')
    def test_get_mp3_duration_error(self, mock_mp3_class, tmp_path):
        """Test getting MP3 duration when error occurs."""
        mock_mp3_class.side_effect = Exception("File error")
        
        file_path = tmp_path / "test.mp3"
        file_path.touch()
        
        handler = PodcastHandler(tmp_path)
        duration = handler._get_mp3_duration(file_path)
        
        assert duration == 0.0
    
    @patch('tonuino_organizer.podcast_handler.MP3')
    def test_is_file_too_short_true(self, mock_mp3_class, tmp_path):
        """Test that file shorter than min_duration returns True."""
        mock_audio = MagicMock()
        mock_audio.info.length = 30.0  # 30 seconds
        mock_mp3_class.return_value = mock_audio
        
        file_path = tmp_path / "short.mp3"
        file_path.touch()
        
        handler = PodcastHandler(tmp_path, min_duration=60.0)
        assert handler._is_file_too_short(file_path) is True
    
    @patch('tonuino_organizer.podcast_handler.MP3')
    def test_is_file_too_short_false(self, mock_mp3_class, tmp_path):
        """Test that file longer than min_duration returns False."""
        mock_audio = MagicMock()
        mock_audio.info.length = 120.0  # 2 minutes
        mock_mp3_class.return_value = mock_audio
        
        file_path = tmp_path / "long.mp3"
        file_path.touch()
        
        handler = PodcastHandler(tmp_path, min_duration=60.0)
        assert handler._is_file_too_short(file_path) is False
    
    def test_get_local_files(self, tmp_path):
        """Test getting local MP3 files."""
        (tmp_path / "episode1.mp3").touch()
        (tmp_path / "episode2.mp3").touch()
        (tmp_path / "other.txt").touch()
        
        handler = PodcastHandler(tmp_path)
        mp3_files = handler.get_local_files()
        
        assert len(mp3_files) == 2
        assert all(f.suffix.lower() == ".mp3" for f in mp3_files)
    
    @patch('tonuino_organizer.podcast_handler.MP3')
    def test_get_local_files_removes_short_files(self, mock_mp3_class, tmp_path):
        """Test that get_local_files removes files that are too short."""
        # Create files
        short_file = tmp_path / "short.mp3"
        long_file = tmp_path / "long.mp3"
        short_file.touch()
        long_file.touch()
        
        # Mock duration responses
        def mock_mp3_side_effect(path):
            mock = MagicMock()
            if path == short_file:
                mock.info.length = 30.0  # Too short
            else:
                mock.info.length = 120.0  # Long enough
            return mock
        
        mock_mp3_class.side_effect = mock_mp3_side_effect
        
        handler = PodcastHandler(tmp_path, min_duration=60.0)
        mp3_files = handler.get_local_files()
        
        # Short file should be removed, only long file remains
        assert len(mp3_files) == 1
        assert mp3_files[0] == long_file
        assert not short_file.exists()  # Should be deleted
    
    @patch('tonuino_organizer.podcast_handler.feedparser')
    @patch('tonuino_organizer.podcast_handler.requests')
    def test_download_episodes_skips_downloaded(self, mock_requests, mock_feedparser, tmp_path):
        """Test that already downloaded URLs are skipped."""
        # Set up feed
        mock_feed = MagicMock()
        mock_entry = MagicMock()
        mock_entry.get.return_value = "Test Episode"
        mock_entry.enclosures = [{'type': 'audio/mpeg', 'href': 'https://example.com/ep1.mp3'}]
        mock_feed.entries = [mock_entry]
        mock_feed.bozo = False
        mock_feedparser.parse.return_value = mock_feed
        
        # Mark URL as already downloaded
        downloaded_file = tmp_path / ".downloaded_files"
        downloaded_file.write_text("https://example.com/ep1.mp3\n")
        
        handler = PodcastHandler(tmp_path)
        downloaded_files = handler.download_episodes("https://example.com/feed.xml")
        
        # Should not download again
        mock_requests.get.assert_not_called()
        assert len(downloaded_files) == 0
    
    @patch('tonuino_organizer.podcast_handler.MP3')
    @patch('tonuino_organizer.podcast_handler.feedparser')
    @patch('tonuino_organizer.podcast_handler.requests')
    def test_download_episodes_rejects_short_files(
        self, mock_requests, mock_feedparser, mock_mp3_class, tmp_path
    ):
        """Test that short files are rejected after download."""
        # Set up feed
        mock_feed = MagicMock()
        mock_entry = MagicMock()
        mock_entry.get.return_value = "Short Episode"
        mock_entry.enclosures = [{'type': 'audio/mpeg', 'href': 'https://example.com/short.mp3'}]
        mock_feed.entries = [mock_entry]
        mock_feed.bozo = False
        mock_feedparser.parse.return_value = mock_feed
        
        # Mock download response
        mock_response = MagicMock()
        mock_response.headers = {'content-length': '1000'}
        mock_response.iter_content.return_value = [b"fake mp3 content"]
        mock_response.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_response
        
        # Mock MP3 duration - return short duration
        mock_audio = MagicMock()
        mock_audio.info.length = 30.0  # Too short
        mock_mp3_class.return_value = mock_audio
        
        handler = PodcastHandler(tmp_path, min_duration=60.0)
        downloaded_files = handler.download_episodes("https://example.com/feed.xml")
        
        # File should be rejected and not returned
        assert len(downloaded_files) == 0
        
        # URL should be in rejected list
        assert "https://example.com/short.mp3" in handler.rejected_urls


class TestProcessPodcast:
    """Tests for process_podcast function."""
    
    def test_process_podcast_no_update(self, tmp_path):
        """Test processing podcast without update."""
        (tmp_path / "episode1.mp3").touch()
        (tmp_path / "episode2.mp3").touch()
        
        mp3_files = process_podcast(
            tmp_path,
            "https://example.com/feed.xml",
            update=False
        )
        
        assert len(mp3_files) == 2
    
    @patch('tonuino_organizer.podcast_handler.feedparser')
    def test_process_podcast_with_update(self, mock_feedparser, tmp_path):
        """Test processing podcast with update."""
        # Mock empty feed (no new episodes)
        mock_feed = MagicMock()
        mock_feed.entries = []
        mock_feed.bozo = False
        mock_feedparser.parse.return_value = mock_feed
        
        # Existing file
        (tmp_path / "episode1.mp3").touch()
        
        mp3_files = process_podcast(
            tmp_path,
            "https://example.com/feed.xml",
            update=True,
            min_duration=60.0
        )
        
        assert len(mp3_files) == 1
    
    def test_process_podcast_custom_min_duration(self, tmp_path):
        """Test processing podcast with custom min_duration."""
        mp3_files = process_podcast(
            tmp_path,
            "https://example.com/feed.xml",
            update=False,
            min_duration=120.0
        )
        
        assert mp3_files == []

