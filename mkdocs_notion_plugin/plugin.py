"""MkDocs plugin for Notion integration."""
from typing import Any, Dict, List, Optional

from mkdocs.config import Config
from mkdocs.config.config_options import Type
from mkdocs.plugins import BasePlugin
from mkdocs.structure.files import Files
from mkdocs.structure.pages import Page

from notion_client import Client
import os
from pathlib import Path
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger("mkdocs.plugins.notion")

class NotionPlugin(BasePlugin):
    """Plugin for publishing MkDocs content to Notion."""

    config_scheme = (
        ("notion_token", Type(str, required=True)),
        ("database_id", Type(str, required=True)),
        ("parent_page_id", Type(str, required=True)),
    )

    def __init__(self):
        """Initialize the plugin."""
        self.notion_token: Optional[str] = None
        self.database_id: Optional[str] = None
        self.parent_page_id: Optional[str] = None
        self.notion: Optional[Client] = None

    def on_config(self, config: Config) -> Config:
        """Process the configuration and initialize Notion client."""
        self.notion_token = self.config["notion_token"]
        self.database_id = self.config["database_id"]
        self.parent_page_id = self.config["parent_page_id"]
        
        # Initialize Notion client
        self.notion = Client(auth=self.notion_token)

        return config

    def _convert_html_to_blocks(self, html_content: str) -> List[Dict[str, Any]]:
        """Convert HTML content to Notion blocks."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find the main content area (typically in <main> or <article>)
        main_content = soup.find(['main', 'article', 'div.content'])
        if not main_content:
            main_content = soup
            logger.warning("Could not find main content area, using entire document")
        
        blocks = []
        for element in main_content.children:
            if element.name is None:  # Skip text nodes
                continue
                
            if element.name == 'h1':
                blocks.append({
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {"rich_text": [{"text": {"content": element.get_text()}}]}
                })
            elif element.name == 'h2':
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {"rich_text": [{"text": {"content": element.get_text()}}]}
                })
            elif element.name == 'p':
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"text": {"content": element.get_text()}}]}
                })
            elif element.name == 'pre':
                code = element.find('code')
                language = code.get('class', [''])[0].replace('language-', '') if code else 'plain text'
                blocks.append({
                    "object": "block",
                    "type": "code",
                    "code": {
                        "language": language,
                        "rich_text": [{"text": {"content": element.get_text()}}]
                    }
                })
            elif element.name in ['ul', 'ol']:
                for li in element.find_all('li', recursive=False):
                    blocks.append({
                        "object": "block",
                        "type": "bulleted_list_item" if element.name == 'ul' else "numbered_list_item",
                        "bulleted_list_item" if element.name == 'ul' else "numbered_list_item": {
                            "rich_text": [{"text": {"content": li.get_text()}}]
                        }
                    })
        
        return blocks

    def on_post_build(self, config: Config) -> None:
        """Publish the generated documentation to Notion after build."""
        site_dir = Path(config["site_dir"])
        
        # Create a new page in Notion for the documentation
        root_page = self.notion.pages.create(
            parent={"page_id": self.parent_page_id},
            properties={
                "title": [{"text": {"content": config["site_name"]}}]
            }
        )
        
        # Process each HTML file in the build directory
        for html_file in site_dir.rglob("*.html"):
            relative_path = html_file.relative_to(site_dir)
            # Skip 404 and search pages
            if relative_path.name in ["404.html", "search.html"]:
                logger.info(f"Skipping {relative_path}")
                continue
            
            logger.info(f"Processing {relative_path}")
            
            with open(html_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            try:
                blocks = self._convert_html_to_blocks(content)
                
                # Create a subpage in Notion
                self.notion.pages.create(
                    parent={"page_id": root_page["id"]},
                    properties={
                        "title": [{"text": {"content": str(relative_path)}}]
                    },
                    children=blocks
                )
                logger.info(f"Created Notion page for {relative_path}")
            except Exception as e:
                logger.error(f"Failed to process {relative_path}: {str(e)}")
