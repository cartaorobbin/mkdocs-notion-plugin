"""MkDocs plugin for Notion integration."""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup, Tag
from mkdocs.config import Config
from mkdocs.config.config_options import Type
from mkdocs.config.defaults import MkDocsConfig
from mkdocs.plugins import BasePlugin
from notion_client import Client

from .blocks import convert_html_to_blocks

logger = logging.getLogger("mkdocs.plugins.notion")


class NotionPlugin(BasePlugin):
    """Plugin for publishing MkDocs content to Notion."""

    # Error messages
    ERROR_NO_TOKEN = (
        "Notion token must be provided either through NOTION_TOKEN environment variable or in mkdocs.yml"  # noqa: S105
    )

    config_scheme = (
        ("notion_token", Type(str, required=True)),
        ("parent_page_id", Type(str, required=True)),
        ("version", Type(str, required=True)),
        ("cache_dir", Type(str, default=".notion_cache")),
    )

    def __init__(self) -> None:
        super().__init__()
        self.notion_token: Optional[str] = None
        self.database_id: Optional[str] = None
        self.parent_page_id: Optional[str] = None
        self.version: Optional[str] = None
        self.cache_dir: str = ".notion_cache"
        self.notion: Optional[Client] = None
        self.pages: List[Dict[str, Any]] = []  # Store page info for navigation

    def _create_docs_table(self) -> str:  # noqa: C901
        """Create a table for documentation in the parent page if it doesn't exist.
        Returns:
            The database ID of the table.
        """
        if self.notion is None:
            raise RuntimeError("Notion client is not initialized")

        # First check if we already have a table in the parent page
        search_response = self.notion.search(query="Projects", filter={"property": "object", "value": "database"})
        if isinstance(search_response, dict):
            results = search_response.get("results", [])
        else:
            # This should never happen in synchronous usage, but handle it just in case
            results = []

        # Check if any of the found databases are in our parent page
        for db in results:
            if not isinstance(db, dict):
                continue

            parent = db.get("parent")
            if not isinstance(parent, dict):
                continue

            if parent.get("page_id") == self.parent_page_id:
                # Check if database has all required properties
                properties = db.get("properties")
                if not isinstance(properties, dict):
                    continue

                required_props = {"Name", "Version", "Last Updated"}
                if all(prop in properties for prop in required_props):
                    db_id = db.get("id")
                    if not db_id:
                        continue
                    logger.info(f"Found existing projects table with ID: {db_id}")
                    return str(db_id)
                else:
                    # Archive the database if schema doesn't match
                    logger.info("Existing table has incorrect schema, recreating...")
                    db_id = db.get("id")
                    if not db_id:
                        continue
                    self.notion.databases.update(database_id=db_id, archived=True)

        # If no table exists, create one
        logger.info("Creating new projects table...")
        new_db_response = self.notion.databases.create(
            parent={"type": "page_id", "page_id": self.parent_page_id},
            title=[{"type": "text", "text": {"content": "Projects"}}],
            properties={"Name": {"title": {}}, "Version": {"rich_text": {}}, "Last Updated": {"date": {}}},
        )

        if not isinstance(new_db_response, dict):
            raise TypeError("Unexpected response from Notion API")

        new_db = new_db_response
        logger.info(f"Created new documentation table with ID: {new_db['id']}")
        return str(new_db["id"])

    def on_config(self, config: Config) -> Optional[MkDocsConfig]:
        """Process the configuration and initialize Notion client."""
        # Get Notion token from environment variable or config
        self.notion_token = os.environ.get("NOTION_TOKEN") or self.config.get("notion_token")
        if not self.notion_token:
            raise ValueError(self.ERROR_NO_TOKEN)

        self.parent_page_id = self.config["parent_page_id"]
        self.version = self.config["version"]

        # Initialize Notion client
        self.notion = Client(auth=self.notion_token)

        # Create or get the documentation table
        self.database_id = self._create_docs_table()

        # Convert Config to MkDocsConfig for type compatibility
        if isinstance(config, MkDocsConfig):
            return config
        return None

    def _get_page_title(self, soup: BeautifulSoup, relative_path: Path) -> str:
        """Extract a meaningful title from the HTML content."""
        # Try to get the first h1 heading
        h1 = soup.find("h1")
        if h1:
            text = h1.get_text()
            return str(text).strip() if text is not None else ""

        # If no h1, try to get the title tag
        title = soup.find("title")
        if title:
            # Remove any theme suffix like ' - Documentation'
            text = title.get_text()
            if text is None:
                return ""
            title_text = str(text).strip()
            if " - " in title_text:
                return str(title_text.split(" - ")[0])
            return title_text

        # Fallback: Clean up the filename
        if relative_path.name == "index.html":
            return relative_path.parent.name.replace("-", " ").replace("_", " ").title()
        return relative_path.stem.replace("-", " ").replace("_", " ").title()

    def _convert_html_to_blocks(self, html_content: str) -> List[Dict[str, Any]]:
        """Convert HTML content to Notion blocks.

        Args:
            html_content: HTML string to convert

        Returns:
            List[Dict[str, Any]]: List of Notion blocks
        """
        return convert_html_to_blocks(html_content)

    def _add_navigation_block(self, current_index: int) -> List[Dict[str, Any]]:
        """Create navigation blocks for the current page."""
        nav_blocks = []

        # Add a divider before navigation
        nav_blocks.append({"object": "block", "type": "divider", "divider": {}})

        # Add navigation heading
        nav_blocks.append(
            {
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": "Navigation"}, "annotations": {"bold": True}}]
                },
            }
        )

        # Create navigation links
        if current_index > 0:
            prev_page = self.pages[current_index - 1]
            nav_blocks.append(
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": "← Previous: "},
                                "annotations": {"italic": True, "color": "gray"},
                            },
                            {
                                "type": "text",
                                "text": {
                                    "content": prev_page["title"],
                                    "link": {
                                        "url": (
                                            f"https://www.notion.so/{prev_page['notion_id'].replace('-', '')}#internal"
                                        )
                                    },
                                },
                                "annotations": {"bold": True, "color": "blue"},
                            },
                        ]
                    },
                }
            )

        if current_index < len(self.pages) - 1:
            next_page = self.pages[current_index + 1]
            nav_blocks.append(
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": "Next: "},
                                "annotations": {"italic": True, "color": "gray"},
                            },
                            {
                                "type": "text",
                                "text": {
                                    "content": next_page["title"] + " →",
                                    "link": {
                                        "url": (
                                            f"https://www.notion.so/{next_page['notion_id'].replace('-', '')}#internal"
                                        )
                                    },
                                },
                                "annotations": {"bold": True, "color": "blue"},
                            },
                        ]
                    },
                }
            )

        # Add a final divider
        nav_blocks.append({"object": "block", "type": "divider", "divider": {}})

        return nav_blocks

    def on_post_build(self, config: MkDocsConfig) -> None:  # noqa: C901
        """Publish the generated documentation to Notion after build."""
        # Create or update the project in the Projects table
        project_name = config["site_name"]
        logger.info(f"Creating/updating project: {project_name}")

        # Process the index page first
        site_dir = Path(config.site_dir)
        index_file = site_dir / "index.html"

        # Read and parse index.html content
        with open(index_file, encoding="utf-8") as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, "html.parser")
        main_content = soup.find("div", {"role": "main"})

        if not main_content:
            logger.warning("No main content found in index.html")
            return

        # Convert HTML elements to Notion blocks
        blocks = self._convert_html_to_blocks(str(main_content))

        # Search for existing project with same name and version
        if self.notion is None:
            raise RuntimeError("Notion client is not initialized")

        if self.database_id is None:
            raise RuntimeError("Database ID is not initialized")

        query_response = self.notion.databases.query(
            database_id=self.database_id,
            filter={
                "and": [
                    {"property": "Name", "title": {"equals": project_name}},
                    {"property": "Version", "rich_text": {"equals": self.version}},
                ]
            },
        )
        if isinstance(query_response, dict):
            results = query_response.get("results", [])
        else:
            # This should never happen in synchronous usage, but handle it just in case
            results = []

        # Create or update the project in the table
        properties = {
            "Name": {"title": [{"text": {"content": project_name}}]},
            "Version": {"rich_text": [{"text": {"content": self.version}}]},
            "Last Updated": {"date": {"start": datetime.now().isoformat()}},
        }

        if results:
            # Delete existing project (this will delete all children too)
            project_page = results[0]
            self.notion.pages.update(project_page["id"], archived=True)
            logger.info(f"Deleted existing project: {project_name} version {self.version}")

        # Create new project
        project_page_response = self.notion.pages.create(
            parent={"database_id": self.database_id}, properties=properties
        )
        if not isinstance(project_page_response, dict):
            raise TypeError("Unexpected response from Notion API")
        project_page = project_page_response
        logger.info(f"Created new project: {project_name} version {self.version}")

        project_id = project_page.get("id")
        if not project_id:
            raise RuntimeError("Project page ID not found in Notion API response")

        # Create index page under the project
        index_page_response = self.notion.pages.create(
            parent={"page_id": project_id},
            properties={"title": [{"text": {"content": project_name}}]},  # Use original name without version
            children=blocks,
        )
        if not isinstance(index_page_response, dict):
            raise TypeError("Unexpected response from Notion API")
        index_page = index_page_response
        logger.info(f"Created index page for {project_name} version {self.version}")

        index_id = index_page.get("id")
        if not index_id:
            raise RuntimeError("Index page ID not found in Notion API response")

        # Store for navigation
        self.pages.append({"title": project_name, "notion_id": index_id})

        # Now create the documentation pages under the parent page
        site_dir = Path(config.site_dir)
        for html_file in site_dir.rglob("*.html"):
            # Skip utility pages
            if html_file.stem in ["404", "search"]:
                continue

            relative_path = html_file.relative_to(site_dir)
            logger.debug(f"Processing {relative_path}")

            # Read and parse HTML content
            with open(html_file, encoding="utf-8") as f:
                html_content = f.read()

            soup = BeautifulSoup(html_content, "html.parser")
            main_content = soup.find("div", {"role": "main"})

            if not main_content:
                logger.warning(f"No main content found in {relative_path}")
                continue

            # Count child elements for logging
            if isinstance(main_content, Tag):
                child_elements = main_content.find_all(recursive=False)
                logger.debug(f"Found {len(child_elements)} child elements in main content")

            # Convert HTML elements to Notion blocks
            blocks = self._convert_html_to_blocks(str(main_content))

            # Get the page title
            title = self._get_page_title(soup, relative_path)
            logger.info(f"Creating Notion page: {title}")

            # Create the child page under the index page
            child_page_response = self.notion.pages.create(
                parent={"page_id": index_id},  # Use the validated index_id from earlier
                properties={"title": [{"text": {"content": title}}]},
                children=blocks,
            )
            if not isinstance(child_page_response, dict):
                raise TypeError("Unexpected response from Notion API")
            child_page = child_page_response
            logger.info(f"Created page: {title}")

            child_id = child_page.get("id")
            if not child_id:
                raise RuntimeError("Child page ID not found in Notion API response")

            # Store page info for navigation
            self.pages.append({"title": title, "notion_id": child_id})

        # Second pass: update pages with navigation
        for i, page_info in enumerate(self.pages):
            try:
                # Add navigation blocks
                nav_blocks = self._add_navigation_block(i)
                if nav_blocks:  # Only update if there are navigation links
                    # Append navigation blocks to the page
                    for block in nav_blocks:
                        self.notion.blocks.children.append(block_id=page_info["notion_id"], children=[block])
                    logger.debug(f"Added navigation to: {page_info['title']}")
            except Exception:
                logger.exception(f"Failed to add navigation to {page_info['path']}")
