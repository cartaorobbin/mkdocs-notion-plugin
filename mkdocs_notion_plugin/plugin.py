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
        ("notion_token", Type(str, required=False)),
        ("parent_page_id", Type(str, required=False)),
        ("version", Type(str, required=False)),
        ("cache_dir", Type(str, default=".notion_cache")),
        ("deploy_on_build", Type(bool, default=False)),
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
        self.theme_name: Optional[str] = None

        # Theme-specific content selectors
        self.THEME_SELECTORS: Dict[str, List[Dict[str, Any]]] = {
            "material": [
                {"tag": "main", "attrs": {"class": "md-main"}},
                {"tag": "div", "attrs": {"class": "md-content"}},
                {"tag": "article", "attrs": {"class": "md-content__inner"}},
            ],
            "readthedocs": [
                {"tag": "div", "attrs": {"role": "main"}},
                {"tag": "div", "attrs": {"class": "document"}},
            ],
            "mkdocs": [
                {"tag": "div", "attrs": {"role": "main"}},
                {"tag": "div", "attrs": {"class": "col-md-9"}},
            ],
            "bootstrap": [
                {"tag": "div", "attrs": {"role": "main"}},
                {"tag": "div", "attrs": {"class": "col-md-9"}},
            ],
            "gitbook": [
                {"tag": "section", "attrs": {"class": "normal"}},
                {"tag": "div", "attrs": {"class": "page-inner"}},
            ],
        }

        # Fallback selectors to try if theme is unknown or not found
        self.FALLBACK_SELECTORS: List[Dict[str, Any]] = [
            {"tag": "main", "attrs": {"class": "md-main"}},  # Material
            {"tag": "div", "attrs": {"role": "main"}},  # ReadTheDocs/MkDocs
            {"tag": "div", "attrs": {"class": "document"}},  # ReadTheDocs
            {"tag": "div", "attrs": {"class": "col-md-9"}},  # Bootstrap/MkDocs
            {"tag": "article"},  # Generic article
            {"tag": "main"},  # Generic main
        ]

    def get_or_create_projects_database(self) -> str:
        """Get existing Projects database or create a new one.
        Returns:
            The database ID.
        """
        if self.notion is None:
            raise RuntimeError("Notion client is not initialized")

        # Search for "Projects" database in parent page
        search_response = self.notion.search(query="Projects", filter={"property": "object", "value": "database"})

        results = search_response.get("results", []) if isinstance(search_response, dict) else []

        # Look for exact match
        for db in results:
            if not isinstance(db, dict):
                continue

            # Get title
            title_list = db.get("title", [])
            if title_list and len(title_list) > 0:
                db_title = title_list[0].get("text", {}).get("content", "")

                # Check exact name and parent page
                if db_title == "Projects":
                    parent = db.get("parent", {})
                    db_parent_id = parent.get("page_id", "")

                    # Normalize IDs (remove hyphens)
                    if (
                        db_parent_id
                        and self.parent_page_id
                        and db_parent_id.replace("-", "") == self.parent_page_id.replace("-", "")
                    ):
                        db_id = db.get("id")
                        if db_id:
                            return str(db_id)

        # Create new database
        new_db_response = self.notion.databases.create(
            parent={"type": "page_id", "page_id": self.parent_page_id},
            title=[{"type": "text", "text": {"content": "Projects"}}],
            properties={"Name": {"title": {}}, "Version": {"rich_text": {}}, "Last Updated": {"date": {}}},
        )

        if isinstance(new_db_response, dict):
            return str(new_db_response["id"])
        else:
            raise TypeError("Unexpected response from Notion API")

    def on_config(self, config: Config) -> Optional[MkDocsConfig]:
        """Process the configuration."""
        # Store configuration values but don't validate them yet
        # Validation happens only when deploying
        self.notion_token = os.environ.get("NOTION_TOKEN") or self.config.get("notion_token")
        self.parent_page_id = self.config.get("parent_page_id")
        self.version = os.environ.get("NOTION_VERSION") or self.config.get("version")

        # Detect theme for content parsing
        self._detect_theme(config)

        # Don't initialize Notion client here - do it only when needed for deployment

        # Convert Config to MkDocsConfig for type compatibility
        if isinstance(config, MkDocsConfig):
            return config
        return None

    def _detect_theme(self, config: Config) -> None:
        """Detect the theme being used from MkDocs configuration."""
        try:
            # Access theme configuration
            theme_config = config.get("theme", {})

            # Handle different theme config formats
            if hasattr(theme_config, "name"):
                # Theme object with name attribute
                self.theme_name = str(theme_config.name)
            elif isinstance(theme_config, dict):
                # Dictionary with name key
                self.theme_name = theme_config.get("name", "mkdocs")
            else:
                # Handle case where theme is just a string
                self.theme_name = str(theme_config) if theme_config else "mkdocs"

            logger.info(f"Detected theme: {self.theme_name}")

            # Log supported themes for debugging
            supported_themes = list(self.THEME_SELECTORS.keys())
            if self.theme_name in supported_themes:
                logger.info(f"Theme '{self.theme_name}' is supported with specific selectors")
            else:
                logger.warning(
                    f"Theme '{self.theme_name}' not in supported list {supported_themes}, will use fallback selectors"
                )

        except Exception as e:
            logger.warning(f"Could not detect theme: {e}, using fallback selectors")
            self.theme_name = "unknown"

    def _find_main_content(self, soup: BeautifulSoup) -> Optional[Tag]:
        """Find the main content element using theme-specific selectors."""
        # Try theme-specific selectors first
        if self.theme_name and self.theme_name in self.THEME_SELECTORS:
            selectors = self.THEME_SELECTORS[self.theme_name]
            logger.debug(f"Trying theme-specific selectors for '{self.theme_name}'")

            for selector in selectors:
                tag_name = selector["tag"]
                attrs = selector.get("attrs", {})

                element = soup.find(tag_name, attrs)
                if element and isinstance(element, Tag):
                    logger.info(f"Found main content using {tag_name} with {attrs}")
                    return element

        # Fallback to trying all known selectors
        logger.debug("Trying fallback selectors")
        for selector in self.FALLBACK_SELECTORS:
            tag_name = selector["tag"]
            attrs = selector.get("attrs", {})

            element = soup.find(tag_name, attrs)
            if element and isinstance(element, Tag):
                logger.info(f"Found main content using fallback selector: {tag_name} with {attrs}")
                return element

        logger.error("Could not find main content with any selector")
        return None

    def _truncate_rich_text(self, rich_text: Dict[str, Any], max_length: int, block_info: str) -> None:
        """Truncate rich text content if it exceeds max length."""
        if rich_text.get("type") == "text":
            content = rich_text.get("text", {}).get("content", "")
            if len(content) > max_length:
                truncated = content[: max_length - 3] + "..."
                rich_text["text"]["content"] = truncated
                logger.warning(f"{block_info}: Truncated from {len(content)} to {len(truncated)} characters")

    def _validate_table_block(self, block: Dict[str, Any], block_idx: int, max_length: int) -> None:
        """Validate and fix table block content."""
        table_data = block.get("table", {})
        children = table_data.get("children", [])

        for row_idx, row in enumerate(children):
            if row.get("type") == "table_row":
                cells = row.get("table_row", {}).get("cells", [])
                for cell_idx, cell in enumerate(cells):
                    for rich_text in cell:
                        self._truncate_rich_text(
                            rich_text, max_length, f"Block {block_idx}: table cell [{row_idx}][{cell_idx}]"
                        )

    def _validate_text_block(self, block: Dict[str, Any], block_idx: int, max_length: int) -> None:
        """Validate and fix text block content."""
        block_type = block.get("type")
        rich_text_list = block.get(block_type, {}).get("rich_text", []) if block_type else []
        for rich_text in rich_text_list:
            self._truncate_rich_text(rich_text, max_length, f"Block {block_idx}: {block_type}")

    def _validate_notion_limits(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and fix blocks to ensure they meet Notion's API limits."""
        MAX_TEXT_LENGTH = 2000
        logger.info(f"Validating {len(blocks)} blocks for Notion limits")

        for i, block in enumerate(blocks):
            block_type = block.get("type")

            if block_type == "table":
                self._validate_table_block(block, i, MAX_TEXT_LENGTH)
            elif block_type in ["paragraph", "heading_1", "heading_2", "heading_3"]:
                self._validate_text_block(block, i, MAX_TEXT_LENGTH)
            elif block_type == "code":
                self._validate_text_block(block, i, MAX_TEXT_LENGTH)

        logger.info(f"Validation complete: {len(blocks)} blocks ready for Notion")
        return blocks

    def _initialize_notion_client(self) -> None:
        """Initialize Notion client and validate configuration."""
        # Validate required configuration
        if not self.notion_token:
            raise ValueError(self.ERROR_NO_TOKEN)

        if not self.parent_page_id:
            raise ValueError("parent_page_id must be provided in mkdocs.yml")

        if not self.version:
            raise ValueError("version must be provided in mkdocs.yml")

        # Initialize Notion client
        self.notion = Client(auth=self.notion_token)

        # Create or get the documentation table
        self.database_id = self.get_or_create_projects_database()

    def _get_page_title(self, soup: BeautifulSoup, relative_path: Path) -> str:
        """Extract a meaningful title from the HTML content."""
        # Try to get the first h1 heading
        h1 = soup.find("h1")
        if h1:
            text = h1.get_text()
            return str(text).strip() if text is not None else ""

        # If no h1, try to get the title tag
        title_element = soup.find("title")
        if title_element:
            # Remove any theme suffix like ' - Documentation'
            text = title_element.get_text()
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

    def on_post_build(self, config: MkDocsConfig) -> None:
        """Publish the generated documentation to Notion after build."""
        # Only deploy automatically if deploy_on_build is enabled
        if not self.config.get("deploy_on_build", False):
            logger.info(
                "Skipping Notion deployment (deploy_on_build is disabled). Use 'mkdocs notion-deploy' to deploy"
                " manually."
            )
            return

        self.deploy_to_notion(config)

    def deploy_to_notion(self, config: MkDocsConfig) -> None:  # noqa: C901
        """Deploy the generated documentation to Notion."""
        # Initialize Notion client and validate configuration only when deploying
        if not self.notion:
            self._initialize_notion_client()

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
        main_content = self._find_main_content(soup)

        if not main_content:
            logger.error("No main content found in index.html - check theme support")
            return

        # Convert HTML elements to Notion blocks
        blocks = self._convert_html_to_blocks(str(main_content))

        # CRITICAL FIX: Ensure all content meets Notion's limits
        blocks = self._validate_notion_limits(blocks)

        # Search for existing project with same name and version
        if self.notion is None:
            raise RuntimeError("Notion client is not initialized")

        if self.database_id is None:
            raise RuntimeError("Database ID is not initialized")

        logger.info(f"Querying database with ID: {self.database_id}")
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
            main_content = self._find_main_content(soup)

            if not main_content:
                logger.warning(f"No main content found in {relative_path}")
                continue

            # Count child elements for logging
            if isinstance(main_content, Tag):
                child_elements = main_content.find_all(recursive=False)
                logger.debug(f"Found {len(child_elements)} child elements in main content")

            # Convert HTML elements to Notion blocks
            blocks = self._convert_html_to_blocks(str(main_content))

            # CRITICAL FIX: Ensure all content meets Notion's limits
            blocks = self._validate_notion_limits(blocks)

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
