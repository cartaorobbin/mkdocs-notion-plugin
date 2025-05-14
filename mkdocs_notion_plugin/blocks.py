"""HTML to Notion block converters."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger("mkdocs.plugins.notion")


class BlockConverter(ABC):
    """Base class for HTML to Notion block converters."""

    @abstractmethod
    def can_convert(self, element: Tag) -> bool:
        """Check if this converter can handle the given HTML element.

        Args:
            element: BeautifulSoup Tag to check

        Returns:
            bool: True if this converter can handle the element
        """
        pass

    @abstractmethod
    def convert(self, element: Tag) -> Optional[Dict[str, Any]]:
        """Convert HTML element to Notion block.

        Args:
            element: BeautifulSoup Tag to convert

        Returns:
            Optional[Dict[str, Any]]: Notion block or None if conversion failed
        """
        pass


class HeadingConverter(BlockConverter):
    """Convert HTML heading elements to Notion heading blocks."""

    def can_convert(self, element: Tag) -> bool:
        return element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]

    def convert(self, element: Tag) -> Optional[Dict[str, Any]]:
        heading_level = int(element.name[1])  # Get number from h1-h6
        heading_type = f"heading_{min(heading_level, 3)}"  # Notion only supports h1-h3

        return {
            "object": "block",
            "type": heading_type,
            heading_type: {"rich_text": [{"type": "text", "text": {"content": element.get_text()}}]},
        }


class ParagraphConverter(BlockConverter):
    """Convert HTML paragraph elements to Notion paragraph blocks."""

    def can_convert(self, element: Tag) -> bool:
        return bool(element.name == "p")

    def convert(self, element: Tag) -> Optional[Dict[str, Any]]:
        return {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": element.get_text()}}]},
        }


class TableConverter(BlockConverter):
    """Convert HTML table elements to Notion table blocks."""

    def can_convert(self, element: Tag) -> bool:
        return bool(element.name == "table")

    def convert(self, element: Tag) -> Optional[Dict[str, Any]]:
        # Extract headers and rows
        headers = []
        thead = element.find("thead")
        if isinstance(thead, Tag):
            headers = [cell.get_text() for cell in thead.find_all(["th", "td"])]

        rows = []
        tbody_elem = element.find("tbody")
        tbody = tbody_elem if isinstance(tbody_elem, Tag) else element
        if isinstance(tbody, Tag):
            for tr in tbody.find_all("tr"):
                if isinstance(tr, Tag):
                    rows.append([cell.get_text() for cell in tr.find_all(["td", "th"])])

        if not rows:
            return None

        # Create table block
        return {
            "object": "block",
            "type": "table",
            "table": {
                "table_width": len(rows[0]),
                "has_column_header": bool(headers),
                "children": (
                    [
                        {
                            "type": "table_row",
                            "table_row": {
                                "cells": [
                                    [{"type": "text", "text": {"content": cell}}]
                                    for cell in (headers if headers else rows[0])
                                ]
                            },
                        }
                    ]
                    + [
                        {
                            "type": "table_row",
                            "table_row": {"cells": [[{"type": "text", "text": {"content": cell}}] for cell in row]},
                        }
                        for row in (rows if headers else rows[1:])
                    ]
                ),
            },
        }


class CodeBlockConverter(BlockConverter):
    """Convert HTML pre/code elements to Notion code blocks."""

    def can_convert(self, element: Tag) -> bool:
        return element.name in ["pre", "code"]

    def convert(self, element: Tag) -> Optional[Dict[str, Any]]:
        code_element = element.find("code") if element.name == "pre" else element
        language = "plain text"  # Default to 'plain text' as required by Notion
        if isinstance(code_element, Tag):
            classes = code_element.get("class")
            if classes:
                for cls in classes:
                    if cls.startswith("language-"):
                        # Convert language identifier to Notion's format
                        lang = cls.replace("language-", "")
                        # Map common language identifiers to Notion's format
                        language_map = {
                            "js": "javascript",
                            "py": "python",
                            "rb": "ruby",
                            "cs": "c#",
                            "ts": "typescript",
                            "sh": "shell",
                            "plain_text": "plain text",
                        }
                    language = language_map.get(lang, lang)
                    break

        return {
            "object": "block",
            "type": "code",
            "code": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": code_element.get_text() if isinstance(code_element, Tag) else str(code_element)
                        },
                    }
                ],
                "language": language,
            },
        }


class BlockFactory:
    """Factory for creating block converters."""

    def __init__(self) -> None:
        """Initialize with all available converters."""
        self.converters = [
            HeadingConverter(),
            ParagraphConverter(),
            TableConverter(),
            CodeBlockConverter(),
        ]

    def get_converter(self, element: Tag) -> Optional[BlockConverter]:
        """Get the appropriate converter for an HTML element.

        Args:
            element: BeautifulSoup Tag to convert

        Returns:
            Optional[BlockConverter]: Matching converter or None if no converter found
        """
        for converter in self.converters:
            if converter.can_convert(element):
                return converter
        return None


def convert_html_to_blocks(html_content: str) -> List[Dict[str, Any]]:  # noqa: C901
    """Convert HTML content to Notion blocks.

    Args:
        html_content: HTML string to convert

    Returns:
        List[Dict[str, Any]]: List of Notion blocks
    """
    soup = BeautifulSoup(html_content, "html.parser")
    blocks = []
    factory = BlockFactory()

    # Find the main content area or use the body
    main_content = soup.find("body") or soup

    # Process elements to avoid duplicates
    if not isinstance(main_content, Tag):
        return []

    for element in main_content.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "table", "pre"], recursive=True):
        # For pre tags, only process if they contain code
        if element.name == "pre" and not element.find("code"):
            continue
        # For standalone code blocks not in pre tags
        if element.name != "pre":
            code_elements = element.find_all("code", recursive=False)
            if code_elements:
                for code in code_elements:
                    converter = factory.get_converter(code)
                    if converter:
                        block = converter.convert(code)
                        if block:
                            blocks.append(block)
                            logger.debug(f"Added {code.name} block: {block['type']}")
                continue
        converter = factory.get_converter(element)
        if converter:
            block = converter.convert(element)
            if block:
                blocks.append(block)
                logger.debug(f"Added {element.name} block: {block['type']}")

    logger.debug(f"Created {len(blocks)} blocks total")
    return blocks
