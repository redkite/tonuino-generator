"""Tests for description module."""

import pytest
import yaml
from pathlib import Path
from tempfile import NamedTemporaryFile

from tonuino_organizer.description import (
    load_description,
    get_description_type,
    get_feed_url,
    get_min_duration,
    DescriptionError,
)


class TestLoadDescription:
    """Tests for load_description function."""
    
    def test_load_valid_static_description(self, tmp_path):
        """Test loading valid static description."""
        desc_file = tmp_path / "description.yaml"
        desc_file.write_text("type: static\n")
        
        data = load_description(tmp_path)
        assert data["type"] == "static"
    
    def test_load_valid_rss_description(self, tmp_path):
        """Test loading valid RSS description."""
        desc_file = tmp_path / "description.yaml"
        desc_file.write_text(
            "type: rss\n"
            "feed_url: https://example.com/feed.xml\n"
        )
        
        data = load_description(tmp_path)
        assert data["type"] == "rss"
        assert data["feed_url"] == "https://example.com/feed.xml"
    
    def test_load_rss_with_min_duration(self, tmp_path):
        """Test loading RSS description with min_duration."""
        desc_file = tmp_path / "description.yaml"
        desc_file.write_text(
            "type: rss\n"
            "feed_url: https://example.com/feed.xml\n"
            "min_duration: 120\n"
        )
        
        data = load_description(tmp_path)
        assert data["type"] == "rss"
        assert data["min_duration"] == 120
    
    def test_missing_description_file(self, tmp_path):
        """Test that missing description file raises error."""
        with pytest.raises(DescriptionError, match="Description file not found"):
            load_description(tmp_path)
    
    def test_invalid_yaml(self, tmp_path):
        """Test that invalid YAML raises error."""
        desc_file = tmp_path / "description.yaml"
        desc_file.write_text("invalid: yaml: content: [\n")
        
        with pytest.raises(DescriptionError, match="Invalid YAML"):
            load_description(tmp_path)
    
    def test_missing_type_field(self, tmp_path):
        """Test that missing type field raises error."""
        desc_file = tmp_path / "description.yaml"
        desc_file.write_text("feed_url: https://example.com/feed.xml\n")
        
        with pytest.raises(DescriptionError, match="must contain 'type' field"):
            load_description(tmp_path)
    
    def test_invalid_type(self, tmp_path):
        """Test that invalid type raises error."""
        desc_file = tmp_path / "description.yaml"
        desc_file.write_text("type: invalid\n")
        
        with pytest.raises(DescriptionError, match="Invalid type"):
            load_description(tmp_path)
    
    def test_rss_missing_feed_url(self, tmp_path):
        """Test that RSS type without feed_url raises error."""
        desc_file = tmp_path / "description.yaml"
        desc_file.write_text("type: rss\n")
        
        with pytest.raises(DescriptionError, match="must contain 'feed_url' field"):
            load_description(tmp_path)
    
    def test_rss_empty_feed_url(self, tmp_path):
        """Test that empty feed_url raises error."""
        desc_file = tmp_path / "description.yaml"
        desc_file.write_text(
            "type: rss\n"
            "feed_url: \n"
        )
        
        with pytest.raises(DescriptionError, match="must be a non-empty string"):
            load_description(tmp_path)
    
    def test_invalid_min_duration_type(self, tmp_path):
        """Test that invalid min_duration type raises error."""
        desc_file = tmp_path / "description.yaml"
        desc_file.write_text(
            "type: rss\n"
            "feed_url: https://example.com/feed.xml\n"
            "min_duration: 'not a number'\n"
        )
        
        with pytest.raises(DescriptionError, match="must be a number"):
            load_description(tmp_path)
    
    def test_negative_min_duration(self, tmp_path):
        """Test that negative min_duration raises error."""
        desc_file = tmp_path / "description.yaml"
        desc_file.write_text(
            "type: rss\n"
            "feed_url: https://example.com/feed.xml\n"
            "min_duration: -10\n"
        )
        
        with pytest.raises(DescriptionError, match="must be a positive number"):
            load_description(tmp_path)
    
    def test_zero_min_duration(self, tmp_path):
        """Test that zero min_duration raises error."""
        desc_file = tmp_path / "description.yaml"
        desc_file.write_text(
            "type: rss\n"
            "feed_url: https://example.com/feed.xml\n"
            "min_duration: 0\n"
        )
        
        with pytest.raises(DescriptionError, match="must be a positive number"):
            load_description(tmp_path)
    
    def test_not_a_dictionary(self, tmp_path):
        """Test that non-dictionary content raises error."""
        desc_file = tmp_path / "description.yaml"
        desc_file.write_text("- item1\n- item2\n")
        
        with pytest.raises(DescriptionError, match="must contain a YAML dictionary"):
            load_description(tmp_path)


class TestGetDescriptionType:
    """Tests for get_description_type function."""
    
    def test_get_static_type(self, tmp_path):
        """Test getting static type."""
        desc_file = tmp_path / "description.yaml"
        desc_file.write_text("type: static\n")
        
        assert get_description_type(tmp_path) == "static"
    
    def test_get_rss_type(self, tmp_path):
        """Test getting RSS type."""
        desc_file = tmp_path / "description.yaml"
        desc_file.write_text(
            "type: rss\n"
            "feed_url: https://example.com/feed.xml\n"
        )
        
        assert get_description_type(tmp_path) == "rss"


class TestGetFeedUrl:
    """Tests for get_feed_url function."""
    
    def test_get_feed_url_for_rss(self, tmp_path):
        """Test getting feed URL for RSS type."""
        desc_file = tmp_path / "description.yaml"
        desc_file.write_text(
            "type: rss\n"
            "feed_url: https://example.com/feed.xml\n"
        )
        
        assert get_feed_url(tmp_path) == "https://example.com/feed.xml"
    
    def test_get_feed_url_for_static_returns_none(self, tmp_path):
        """Test that static type returns None for feed_url."""
        desc_file = tmp_path / "description.yaml"
        desc_file.write_text("type: static\n")
        
        assert get_feed_url(tmp_path) is None


class TestGetMinDuration:
    """Tests for get_min_duration function."""
    
    def test_get_min_duration_from_file(self, tmp_path):
        """Test getting min_duration from file."""
        desc_file = tmp_path / "description.yaml"
        desc_file.write_text(
            "type: rss\n"
            "feed_url: https://example.com/feed.xml\n"
            "min_duration: 120\n"
        )
        
        assert get_min_duration(tmp_path) == 120
    
    def test_get_min_duration_default(self, tmp_path):
        """Test that default is used when min_duration not specified."""
        desc_file = tmp_path / "description.yaml"
        desc_file.write_text(
            "type: rss\n"
            "feed_url: https://example.com/feed.xml\n"
        )
        
        assert get_min_duration(tmp_path) == 60.0
        assert get_min_duration(tmp_path, default=90.0) == 90.0
    
    def test_get_min_duration_custom_default(self, tmp_path):
        """Test that custom default is used."""
        desc_file = tmp_path / "description.yaml"
        desc_file.write_text(
            "type: static\n"
        )
        
        assert get_min_duration(tmp_path, default=180.0) == 180.0

