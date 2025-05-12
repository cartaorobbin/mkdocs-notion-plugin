"""MkDocs Notion Plugin."""
from mkdocs_notion_plugin.plugin import NotionPlugin

__version__ = "0.0.1"

def get_plugin():
    """Return the plugin to be used by MkDocs."""
    return NotionPlugin