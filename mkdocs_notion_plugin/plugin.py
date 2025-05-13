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

    def _get_page_title(self, soup: BeautifulSoup, relative_path: Path) -> str:
        """Extract a meaningful title from the HTML content."""
        # Try to get the first h1 heading
        h1 = soup.find('h1')
        if h1:
            return h1.get_text().strip()
        
        # If no h1, try to get the title tag
        title = soup.find('title')
        if title:
            # Remove any theme suffix like ' - Documentation'
            title_text = title.get_text().strip()
            if ' - ' in title_text:
                return title_text.split(' - ')[0]
            return title_text
        
        # Fallback: Clean up the filename
        if relative_path.name == 'index.html':
            return relative_path.parent.name.replace('-', ' ').replace('_', ' ').title()
        return relative_path.stem.replace('-', ' ').replace('_', ' ').title()

    def _convert_html_to_blocks(self, html_content: str) -> List[Dict[str, Any]]:
        """Convert HTML content to Notion blocks."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find the main content area in MkDocs ReadTheDocs theme
        document = soup.find('div', {'role': 'main', 'class': 'document'})
        main_content = document.find('div', {'class': 'section'}) if document else None
        if not main_content:
            main_content = soup
            logger.warning("Could not find main content area, using entire document")
        
        blocks = []
        logger.info(f"Found {len(list(main_content.children))} child elements in main content")
        for element in main_content.children:
            if element.name is None:  # Skip text nodes
                continue
            logger.info(f"Processing element: {element.name}")
                
            block = None
            if element.name == 'h1':
                block = {
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {"rich_text": [{"text": {"content": element.get_text()}}]}
                }
            elif element.name == 'h2':
                block = {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {"rich_text": [{"text": {"content": element.get_text()}}]}
                }
            elif element.name == 'p':
                block = {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"text": {"content": element.get_text()}}]}
                }
            elif element.name == 'pre':
                code = element.find('code')
                language = code.get('class', [''])[0].replace('language-', '') if code else 'plain text'
                block = {
                    "object": "block",
                    "type": "code",
                    "code": {
                        "language": language,
                        "rich_text": [{"text": {"content": element.get_text()}}]}
                }
            elif element.name in ['ul', 'ol']:
                for li in element.find_all('li', recursive=False):
                    list_block = {
                        "object": "block",
                        "type": "bulleted_list_item" if element.name == 'ul' else "numbered_list_item",
                        "bulleted_list_item" if element.name == 'ul' else "numbered_list_item": {
                            "rich_text": [{"text": {"content": li.get_text()}}]}
                    }
                    blocks.append(list_block)
                    logger.info(f"Added {element.name} item: {li.get_text()[:50]}...")
                continue  # Skip the main block append since we handled the items
            elif element.name == 'blockquote':
                block = {
                    "object": "block",
                    "type": "quote",
                    "quote": {"rich_text": [{"text": {"content": element.get_text()}}]}
                }
            elif element.name == 'table':
                rows = []
                # Get headers
                headers = [th.get_text() for th in element.find('thead').find_all('th')] if element.find('thead') else []
                # Get rows
                tbody = element.find('tbody')
                if tbody:
                    for tr in tbody.find_all('tr'):
                        rows.append([td.get_text() for td in tr.find_all('td')])
                
                block = {
                    "object": "block",
                    "type": "table",
                    "table": {
                        "table_width": len(headers) if headers else (len(rows[0]) if rows else 1),
                        "has_column_header": bool(headers),
                        "has_row_header": False,
                        "children": [{
                            "type": "table_row",
                            "table_row": {
                                "cells": [[{"type": "text", "text": {"content": cell}}] for cell in (headers if headers else rows[0])]
                            }
                        }] + [{
                            "type": "table_row",
                            "table_row": {
                                "cells": [[{"type": "text", "text": {"content": cell}}] for cell in row]
                            }
                        } for row in (rows if headers else rows[1:])]
                    }
                }
        
            if block:
                blocks.append(block)
                logger.info(f"Added {element.name} block: {block['type']}")
        
        logger.info(f"Created {len(blocks)} blocks total")
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
                soup = BeautifulSoup(content, 'html.parser')
                page_title = self._get_page_title(soup, relative_path)
                blocks = self._convert_html_to_blocks(content)
                
                # Create a subpage in Notion
                self.notion.pages.create(
                    parent={"page_id": root_page["id"]},
                    properties={
                        "title": [{"text": {"content": page_title}}]
                    },
                    children=blocks
                )
                logger.info(f"Created Notion page: {page_title}")
                logger.info(f"Created Notion page for {relative_path}")
            except Exception as e:
                logger.error(f"Failed to process {relative_path}: {str(e)}")
