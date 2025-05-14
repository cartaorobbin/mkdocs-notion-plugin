"""Tests for the NotionPlugin.

This module contains unit tests for the NotionPlugin class.
"""

import pytest
from mkdocs.config import Config
from mkdocs.config.base import ValidationError

from mkdocs_notion_plugin.plugin import NotionPlugin

# Test constants to avoid hardcoded credentials in assertions
TEST_TOKEN = "test-token"  # noqa: S105
TEST_DB_ID = "test-db-id"
TEST_CACHE_DIR = "custom-cache"


def test_plugin_initialization():
    """Test that the plugin initializes correctly.

    Returns:
        None
    """
    plugin = NotionPlugin()
    assert plugin.notion_token is None

    assert plugin.cache_dir == ".notion_cache"


def test_plugin_config():
    """Test that the plugin configuration works correctly.

    Returns:
        None
    """
    plugin = NotionPlugin()
    config = {
        "notion_token": TEST_TOKEN,

        "cache_dir": TEST_CACHE_DIR,
    }
    plugin.load_config(config)

    assert plugin.config["notion_token"] == TEST_TOKEN

    assert plugin.config["cache_dir"] == TEST_CACHE_DIR


def test_plugin_required_config():
    """Test that the plugin requires notion_token."""

    Returns:
        None
    """
    plugin = NotionPlugin()
    config = {}

    with pytest.raises(ValidationError):
        plugin.load_config(config)


def test_on_config():
    """Test that on_config sets up the plugin correctly.

    Returns:
        None
    """
    plugin = NotionPlugin()
    config = Config(schema=[])
    config_dict = {
        "notion_token": TEST_TOKEN,

        "cache_dir": TEST_CACHE_DIR,
    }
    plugin.load_config(config_dict)

    result = plugin.on_config(config)

    assert isinstance(result, Config)
    assert plugin.notion_token == TEST_TOKEN

    assert plugin.cache_dir == TEST_CACHE_DIR


def test_on_files():
    """Test that on_files processes the files correctly.

    Returns:
        None
    """
    plugin = NotionPlugin()
    config = Config(schema=[])
    result = plugin.on_files([], config)

    assert result == []


def test_on_page_markdown():
    """Test that on_page_markdown processes the markdown correctly.

    Returns:
        None
    """
    plugin = NotionPlugin()
    markdown = "# Test"
    config = Config(schema=[])

    result = plugin.on_page_markdown(markdown, None, config, [])

    assert result == markdown  # For now, no modifications are made
