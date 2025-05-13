"""Tests for the NotionPlugin."""
import pytest
from mkdocs.config import Config
from mkdocs.structure.files import Files

from mkdocs_notion_plugin.plugin import NotionPlugin


def test_plugin_initialization():
    """Test that the plugin initializes correctly."""
    plugin = NotionPlugin()
    assert plugin.notion_token is None
    assert plugin.database_id is None
    assert plugin.cache_dir == ".notion_cache"


def test_plugin_config():
    """Test that the plugin configuration works correctly."""
    plugin = NotionPlugin()
    config = {
        "notion_token": "test-token",
        "database_id": "test-db-id",
        "cache_dir": "custom-cache",
    }
    plugin.load_config(config)

    assert plugin.config["notion_token"] == "test-token"
    assert plugin.config["database_id"] == "test-db-id"
    assert plugin.config["cache_dir"] == "custom-cache"


def test_plugin_required_config():
    """Test that the plugin requires notion_token and database_id."""
    plugin = NotionPlugin()
    config = {}

    with pytest.raises(Exception):
        plugin.load_config(config)


def test_on_config():
    """Test that on_config sets up the plugin correctly."""
    plugin = NotionPlugin()
    config = Config(schema=[])
    config_dict = {
        "notion_token": "test-token",
        "database_id": "test-db-id",
        "cache_dir": "custom-cache",
    }
    plugin.load_config(config_dict)

    result = plugin.on_config(config)

    assert isinstance(result, Config)
    assert plugin.notion_token == "test-token"
    assert plugin.database_id == "test-db-id"
    assert plugin.cache_dir == "custom-cache"


def test_on_files():
    """Test that on_files processes the files correctly."""
    plugin = NotionPlugin()
    config = Config(schema=[])
    files = Files([])

    result = plugin.on_files(files, config)

    assert isinstance(result, Files)


def test_on_page_markdown():
    """Test that on_page_markdown processes the markdown correctly."""
    plugin = NotionPlugin()
    markdown = "# Test"
    config = Config(schema=[])
    files = Files([])

    result = plugin.on_page_markdown(markdown, None, config, files)

    assert isinstance(result, str)
    assert result == markdown  # For now, no modifications are made
