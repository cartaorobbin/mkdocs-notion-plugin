"""Tests for the NotionPlugin.

This module contains unit tests for the NotionPlugin class.
"""


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
