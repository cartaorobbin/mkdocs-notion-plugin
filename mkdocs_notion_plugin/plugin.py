"""MkDocs plugin for Notion integration."""
from typing import Any, Dict, List, Optional
from datetime import datetime

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
        ("version", Type(str, required=True)),
    )

    def __init__(self):
        """Initialize the plugin."""
        self.notion_token: Optional[str] = None
        self.database_id: Optional[str] = None
        self.parent_page_id: Optional[str] = None
        self.version: Optional[str] = None
        self.notion: Optional[Client] = None
        self.pages: List[Dict[str, Any]] = []  # Store page info for navigation

    def _create_docs_table(self) -> str:
        """Create a table for documentation in the parent page if it doesn't exist.
        Returns:
            The database ID of the table.
        """
        # First check if we already have a table in the parent page
        results = self.notion.search(
            query="Projects",
            filter={
                "property": "object",
                "value": "database"
            }
        ).get("results", [])
        
        # Check if any of the found databases are in our parent page
        for db in results:
            if db.get("parent", {}).get("page_id") == self.parent_page_id:
                # Check if database has all required properties
                properties = db.get("properties", {})
                required_props = {"Name", "Version", "Last Updated"}
                if all(prop in properties for prop in required_props):
                    logger.info(f"Found existing projects table with ID: {db['id']}")
                    return db['id']
                else:
                    # Archive the database if schema doesn't match
                    logger.info("Existing table has incorrect schema, recreating...")
                    self.notion.databases.update(
                        database_id=db["id"],
                        archived=True
                    )
        
        # If no table exists, create one
        logger.info("Creating new projects table...")
        new_db = self.notion.databases.create(
            parent={"type": "page_id", "page_id": self.parent_page_id},
            title=[{"type": "text", "text": {"content": "Projects"}}],
            properties={
                "Name": {"title": {}},
                "Version": {"rich_text": {}},
                "Last Updated": {"date": {}}
            }
        )
        
        logger.info(f"Created new documentation table with ID: {new_db['id']}")
        return new_db['id']

    def on_config(self, config: Config) -> Config:
        """Process the configuration and initialize Notion client."""
        self.notion_token = self.config["notion_token"]
        self.database_id = self.config["database_id"]
        self.parent_page_id = self.config["parent_page_id"]
        self.version = self.config["version"]
        
        # Initialize Notion client
        self.notion = Client(auth=self.notion_token)
        
        # Create or get the documentation table
        self.database_id = self._create_docs_table()

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
                code_element = element.find('code')
                if code_element:
                    # Get language from class (e.g., 'language-mermaid' -> 'mermaid')
                    classes = code_element.get('class', [])
                    language = ''
                    for cls in classes:
                        if cls.startswith('language-'):
                            language = cls.replace('language-', '')
                            break
                    
                    # Get raw content, preserving newlines and whitespace
                    content = code_element.string if code_element.string else code_element.get_text()
                    content = content.strip()
                    
                    # Get the language, defaulting to plain text
                    language = language.lower() if language else "plain text"
                    
                    # Create the code block
                    block = {
                        "object": "block",
                        "type": "code",
                        "code": {
                            "rich_text": [{"type": "text", "text": {"content": content}}],
                            "language": language,
                        }
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

    def _add_navigation_block(self, current_index: int) -> List[Dict[str, Any]]:
        """Create navigation blocks for the current page."""
        nav_blocks = []
        
        # Add a divider before navigation
        nav_blocks.append({
            "object": "block",
            "type": "divider",
            "divider": {}
        })
        
        # Add navigation heading
        nav_blocks.append({
            "object": "block",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": "Navigation"},
                    "annotations": {"bold": True}
                }]
            }
        })
        
        # Create navigation links
        if current_index > 0:
            prev_page = self.pages[current_index - 1]
            nav_blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": "← Previous: "},
                        "annotations": {"italic": True, "color": "gray"}
                    }, {
                        "type": "text",
                        "text": {"content": prev_page['title'], "link": {"url": f"https://www.notion.so/{prev_page['notion_id'].replace('-', '')}#internal"}},
                        "annotations": {"bold": True, "color": "blue"}
                    }]
                }
            })
        
        if current_index < len(self.pages) - 1:
            next_page = self.pages[current_index + 1]
            nav_blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": "Next: "},
                        "annotations": {"italic": True, "color": "gray"}
                    }, {
                        "type": "text",
                        "text": {"content": next_page['title'] + " →", "link": {"url": f"https://www.notion.so/{next_page['notion_id'].replace('-', '')}#internal"}},
                        "annotations": {"bold": True, "color": "blue"}
                    }]
                }
            })
        
        # Add a final divider
        nav_blocks.append({
            "object": "block",
            "type": "divider",
            "divider": {}
        })
        
        return nav_blocks

    def on_post_build(self, config: Config) -> None:
        """Publish the generated documentation to Notion after build."""
        # Create or update the project in the Projects table
        project_name = config["site_name"]
        logger.info(f"Creating/updating project: {project_name}")

        # Process the index page first
        site_dir = Path(config.site_dir)
        index_file = site_dir / "index.html"
        
        # Read and parse index.html content
        with open(index_file, "r", encoding="utf-8") as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, "html.parser")
        main_content = soup.find("div", {"role": "main"})

        if not main_content:
            logger.warning("No main content found in index.html")
            return

        # Convert HTML elements to Notion blocks
        blocks = self._convert_html_to_blocks(str(main_content))

        # Search for existing project with same name and version
        results = self.notion.databases.query(
            database_id=self.database_id,
            filter={
                "and": [
                    {
                        "property": "Name",
                        "title": {
                            "equals": project_name
                        }
                    },
                    {
                        "property": "Version",
                        "rich_text": {
                            "equals": self.version
                        }
                    }
                ]
            }
        ).get("results", [])

        # Create or update the project in the table
        properties = {
            "Name": {
                "title": [{
                    "text": {
                        "content": project_name
                    }
                }]
            },
            "Version": {
                "rich_text": [{
                    "text": {
                        "content": self.version
                    }
                }]
            },
            "Last Updated": {
                "date": {
                    "start": datetime.now().isoformat()
                }
            }
        }

        if results:
            # Delete existing project (this will delete all children too)
            project_page = results[0]
            self.notion.pages.update(project_page["id"], archived=True)
            logger.info(f"Deleted existing project: {project_name} version {self.version}")

        # Create new project
        project_page = self.notion.pages.create(
            parent={"database_id": self.database_id},
            properties=properties
        )
        logger.info(f"Created new project: {project_name} version {self.version}")

        # Create index page under the project
        index_page = self.notion.pages.create(
            parent={"page_id": project_page["id"]},
            properties={
                "title": [{"text": {"content": project_name}}]  # Use original name without version
            },
            children=blocks
        )
        logger.info(f"Created index page for {project_name} version {self.version}")

        # Store for navigation
        self.pages.append({
            "title": project_name,
            "notion_id": index_page["id"]
        })

        # Now create the documentation pages under the parent page
        site_dir = Path(config.site_dir)
        for html_file in site_dir.rglob("*.html"):
            # Skip utility pages
            if html_file.stem in ["404", "search"]:
                continue

            relative_path = html_file.relative_to(site_dir)
            logger.info(f"Processing {relative_path}")

            # Read and parse HTML content
            with open(html_file, "r", encoding="utf-8") as f:
                html_content = f.read()

            soup = BeautifulSoup(html_content, "html.parser")
            main_content = soup.find("div", {"role": "main"})

            if not main_content:
                logger.warning(f"No main content found in {relative_path}")
                continue

            # Count child elements for logging
            child_elements = main_content.find_all(recursive=False)
            logger.info(f"Found {len(child_elements)} child elements in main content")

            # Convert HTML elements to Notion blocks
            blocks = self._convert_html_to_blocks(str(main_content))

            # Get the page title
            title = self._get_page_title(soup, relative_path)
            logger.info(f"Creating Notion page: {title}")

            # Create the child page under the index page
            child_page = self.notion.pages.create(
                parent={"page_id": index_page['id']},
                properties={
                    "title": [{"text": {"content": title}}]
                },
                children=blocks
            )
            logger.info(f"Created page: {title}")

            # Store page info for navigation
            self.pages.append({
                "title": title,
                "notion_id": child_page["id"]
            })

        # Second pass: update pages with navigation
        for i, page_info in enumerate(self.pages):
            try:
                # Add navigation blocks
                nav_blocks = self._add_navigation_block(i)
                if nav_blocks:  # Only update if there are navigation links
                    # Append navigation blocks to the page
                    for block in nav_blocks:
                        self.notion.blocks.children.append(
                            block_id=page_info['notion_id'],
                            children=[block]
                        )
                    logger.info(f"Added navigation to: {page_info['title']}")
            except Exception as e:
                logger.error(f"Failed to add navigation to {page_info['path']}: {str(e)}")
