"""HTML to Notion block converters."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger("mkdocs.plugins.notion")

# Notion API limits
NOTION_MAX_TEXT_LENGTH = 2000
NOTION_MAX_BLOCKS_PER_PAGE = 100


def truncate_text_content(content: str, max_length: int = NOTION_MAX_TEXT_LENGTH) -> str:
    """Truncate text content to fit Notion's limits.

    Args:
        content: Text content to truncate
        max_length: Maximum allowed length

    Returns:
        str: Truncated content with ellipsis if needed
    """
    if len(content) <= max_length:
        return content

    # Truncate and add ellipsis
    truncated = content[: max_length - 3] + "..."
    logger.warning(f"Content truncated from {len(content)} to {len(truncated)} characters")
    return truncated


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


class TitleBlockConverter(BlockConverter):
    """Convert HTML title elements to Notion heading blocks."""

    def can_convert(self, element: Tag) -> bool:
        return element.name == "title"

    def convert(self, element: Tag) -> Optional[Dict[str, Any]]:
        content = truncate_text_content(element.get_text().strip())

        # Skip empty titles or very short titles
        if not content or len(content) < 3:
            return None

        # Convert title to heading_1
        return {
            "object": "block",
            "type": "heading_1",
            "heading_1": {"rich_text": [{"type": "text", "text": {"content": content}}]},
        }


class HeadingConverter(BlockConverter):
    """Convert HTML heading elements to Notion heading blocks."""

    def can_convert(self, element: Tag) -> bool:
        return element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]

    def convert(self, element: Tag) -> Optional[Dict[str, Any]]:
        heading_level = int(element.name[1])  # Get number from h1-h6
        heading_type = f"heading_{min(heading_level, 3)}"  # Notion only supports h1-h3
        content = truncate_text_content(element.get_text().strip())

        return {
            "object": "block",
            "type": heading_type,
            heading_type: {"rich_text": [{"type": "text", "text": {"content": content}}]},
        }


class ParagraphConverter(BlockConverter):
    """Convert HTML paragraph elements to Notion paragraph blocks."""

    def can_convert(self, element: Tag) -> bool:
        return bool(element.name == "p")

    def convert(self, element: Tag) -> Optional[Dict[str, Any]]:
        content = truncate_text_content(element.get_text().strip())

        return {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": content}}]},
        }


class TableConverter(BlockConverter):
    """Convert HTML table elements to Notion table blocks."""

    # Notion limits
    MAX_CELL_LENGTH = 2000
    MAX_TABLE_WIDTH = 5  # Notion's maximum table width

    def can_convert(self, element: Tag) -> bool:
        return bool(element.name == "table")

    def _is_code_highlight_table(self, element: Tag) -> bool:
        """Check if this is a code highlighting table that should be converted to a code block."""
        # Check for common code highlighting table classes
        classes_raw: Union[str, List[str]] = element.get("class", [])
        classes = [classes_raw] if isinstance(classes_raw, str) else classes_raw

        is_highlight_table = any(cls in ["highlighttable", "codehilitetable", "highlight"] for cls in classes)

        # Also check if it's inside a highlight div
        parent_div = element.find_parent("div", class_="highlight")
        is_in_highlight_div = parent_div is not None

        # Check if it contains code cells
        has_code_cell = element.find("td", class_="code") is not None

        result = is_highlight_table or (is_in_highlight_div and has_code_cell)

        if result:
            logger.debug(
                f"Detected code highlighting table: classes={classes}, in_highlight_div={is_in_highlight_div},"
                f" has_code_cell={has_code_cell}"
            )

        return result

    def _convert_code_table_to_code_block(self, element: Tag) -> Optional[Dict[str, Any]]:
        """Convert a code highlighting table to a simple code block."""
        # Look for the code content in the table
        code_cell = element.find("td", class_="code")
        if not code_cell:
            # Fallback: look for any td with code content
            code_cell = element.find("td")

        if not code_cell:
            logger.warning("Could not find code content in highlighting table")
            return None

        # Extract the actual code text, stripping HTML tags
        code_element = code_cell.find("code") or code_cell.find("pre") or code_cell
        code_content = code_element.get_text() if isinstance(code_element, Tag) else str(code_element)

        # Truncate if necessary
        truncated_content = truncate_text_content(code_content.strip())

        # Use the same language validation as CodeBlockConverter
        language = self._validate_language_for_notion(element)

        logger.info(f"Converted code highlighting table to code block (language: {language})")

        return {
            "object": "block",
            "type": "code",
            "code": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": truncated_content},
                    }
                ],
                "language": language,
            },
        }

    def _validate_language_for_notion(self, element: Tag) -> str:
        """Validate and map language to Notion's supported languages."""
        # Notion's supported languages (from the API error message)
        notion_supported_languages = {
            "abap",
            "abc",
            "agda",
            "arduino",
            "ascii art",
            "assembly",
            "bash",
            "basic",
            "bnf",
            "c",
            "clojure",
            "coffeescript",
            "coq",
            "css",
            "dart",
            "dhall",
            "diff",
            "docker",
            "ebnf",
            "elixir",
            "elm",
            "erlang",
            "f#",
            "flow",
            "fortran",
            "gherkin",
            "glsl",
            "go",
            "graphql",
            "groovy",
            "haskell",
            "hcl",
            "html",
            "idris",
            "java",
            "javascript",
            "json",
            "julia",
            "kotlin",
            "latex",
            "less",
            "lisp",
            "livescript",
            "llvm ir",
            "lua",
            "makefile",
            "markdown",
            "markup",
            "matlab",
            "mathematica",
            "mermaid",
            "nix",
            "notion formula",
            "objective-c",
            "ocaml",
            "pascal",
            "perl",
            "php",
            "plain text",
            "powershell",
            "prolog",
            "protobuf",
            "purescript",
            "python",
            "r",
            "racket",
            "reason",
            "ruby",
            "rust",
            "sass",
            "scala",
            "scheme",
            "scss",
            "shell",
            "smalltalk",
            "solidity",
            "sql",
            "swift",
            "toml",
            "typescript",
            "vb.net",
            "verilog",
            "vhdl",
            "visual basic",
            "webassembly",
            "xml",
            "yaml",
            "java/c/c++/c#",
        }

        # Map common language identifiers to Notion's supported languages
        language_map = {
            "js": "javascript",
            "py": "python",
            "rb": "ruby",
            "cs": "c#",
            "ts": "typescript",
            "sh": "shell",
            "bash": "shell",
            "plain_text": "plain text",
            "yml": "yaml",
            "dockerfile": "docker",
            "md": "markdown",
            "tex": "latex",
            "c++": "java/c/c++/c#",
            "cpp": "java/c/c++/c#",
            "csharp": "c#",
            "jinja2": "html",  # Map jinja2 templates to HTML
            "jinja": "html",  # Map jinja templates to HTML
            "j2": "html",  # Map j2 templates to HTML
            "django": "html",  # Map django templates to HTML
            "handlebars": "html",  # Map handlebars templates to HTML
            "mustache": "html",  # Map mustache templates to HTML
            "twig": "html",  # Map twig templates to HTML
            "liquid": "html",  # Map liquid templates to HTML
            "vue": "html",  # Map vue templates to HTML
            "svelte": "html",  # Map svelte templates to HTML
            "jsx": "javascript",  # Map JSX to JavaScript
            "tsx": "typescript",  # Map TSX to TypeScript
        }

        # Try to detect language from classes
        language = "plain text"
        for elem in element.find_all(class_=True):
            classes = elem.get("class", [])
            if isinstance(classes, str):
                classes = [classes]
            for cls in classes:
                if cls.startswith("language-"):
                    lang = cls.replace("language-", "").lower()
                    mapped_lang = language_map.get(lang, lang)

                    # Validate that the language is supported by Notion
                    if mapped_lang in notion_supported_languages:
                        return mapped_lang
                    else:
                        logger.warning(f"Unsupported language '{lang}' (mapped to '{mapped_lang}'), using 'plain text'")
                        return "plain text"
                elif cls.startswith("highlight-"):
                    lang = cls.replace("highlight-", "").lower()
                    mapped_lang = language_map.get(lang, lang)

                    # Validate that the language is supported by Notion
                    if mapped_lang in notion_supported_languages:
                        return mapped_lang
                    else:
                        logger.warning(f"Unsupported language '{lang}' (mapped to '{mapped_lang}'), using 'plain text'")
                        return "plain text"

        return language

    def _truncate_cell_content(self, content: str) -> str:
        """Truncate cell content to fit Notion's limits."""
        original_length = len(content)
        truncated = truncate_text_content(content, self.MAX_CELL_LENGTH)
        if original_length > self.MAX_CELL_LENGTH:
            logger.info(f"Table cell truncated from {original_length} to {len(truncated)} characters")
        return truncated

    def _extract_table_headers(self, element: Tag) -> List[str]:
        """Extract table headers."""
        headers = []
        thead = element.find("thead")
        if isinstance(thead, Tag):
            headers = [self._truncate_cell_content(cell.get_text().strip()) for cell in thead.find_all(["th", "td"])]
            logger.debug(f"Found {len(headers)} headers")
        return headers

    def _extract_table_rows(self, element: Tag) -> List[List[str]]:
        """Extract table rows."""
        rows = []
        tbody_elem = element.find("tbody")
        tbody = tbody_elem if isinstance(tbody_elem, Tag) else element
        if isinstance(tbody, Tag):
            for i, tr in enumerate(tbody.find_all("tr")):
                if isinstance(tr, Tag):
                    row = [self._truncate_cell_content(cell.get_text().strip()) for cell in tr.find_all(["td", "th"])]
                    rows.append(row)
                    # Log long cells for debugging
                    for j, cell_content in enumerate(row):
                        if len(cell_content) > 1900:  # Close to limit
                            logger.warning(f"Large cell at row {i}, col {j}: {len(cell_content)} chars")
        return rows

    def convert(self, element: Tag) -> Optional[Dict[str, Any]]:
        logger.debug(f"Converting table with {len(element.find_all('tr'))} rows")

        # Check if this is a code highlighting table - convert to code block instead
        if self._is_code_highlight_table(element):
            logger.info("Converting code highlighting table to code block")
            return self._convert_code_table_to_code_block(element)

        # Extract headers and rows for regular tables
        headers = self._extract_table_headers(element)
        rows = self._extract_table_rows(element)

        if not rows:
            logger.debug("No table rows found, skipping table")
            return None

        # Limit table width to Notion's maximum
        table_width = min(len(rows[0]) if rows else 0, self.MAX_TABLE_WIDTH)
        if headers:
            headers = headers[:table_width]
        rows = [row[:table_width] for row in rows]

        # Log if table was truncated
        original_width = len(rows[0]) if rows else 0
        if original_width > table_width:
            logger.warning(f"Table width reduced from {original_width} to {table_width} columns to fit Notion limits")

        logger.info(f"Creating table with {len(rows)} rows and {table_width} columns")

        # Create table block
        return {
            "object": "block",
            "type": "table",
            "table": {
                "table_width": table_width,
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

        # Comprehensive mapping of language identifiers to Notion's supported languages
        # Based on the error message, these are the languages Notion supports
        notion_supported_languages = {
            "abap",
            "abc",
            "agda",
            "arduino",
            "ascii art",
            "assembly",
            "bash",
            "basic",
            "bnf",
            "c",
            "clojure",
            "coffeescript",
            "coq",
            "css",
            "dart",
            "dhall",
            "diff",
            "docker",
            "ebnf",
            "elixir",
            "elm",
            "erlang",
            "f#",
            "flow",
            "fortran",
            "gherkin",
            "glsl",
            "go",
            "graphql",
            "groovy",
            "haskell",
            "hcl",
            "html",
            "idris",
            "java",
            "javascript",
            "json",
            "julia",
            "kotlin",
            "latex",
            "less",
            "lisp",
            "livescript",
            "llvm ir",
            "lua",
            "makefile",
            "markdown",
            "markup",
            "matlab",
            "mathematica",
            "mermaid",
            "nix",
            "notion formula",
            "objective-c",
            "ocaml",
            "pascal",
            "perl",
            "php",
            "plain text",
            "powershell",
            "prolog",
            "protobuf",
            "purescript",
            "python",
            "r",
            "racket",
            "reason",
            "ruby",
            "rust",
            "sass",
            "scala",
            "scheme",
            "scss",
            "shell",
            "smalltalk",
            "solidity",
            "sql",
            "swift",
            "toml",
            "typescript",
            "vb.net",
            "verilog",
            "vhdl",
            "visual basic",
            "webassembly",
            "xml",
            "yaml",
            "java/c/c++/c#",
        }

        # Map common language identifiers to Notion's supported languages
        language_map = {
            "js": "javascript",
            "py": "python",
            "rb": "ruby",
            "cs": "c#",
            "ts": "typescript",
            "sh": "shell",
            "bash": "shell",
            "plain_text": "plain text",
            "yml": "yaml",
            "dockerfile": "docker",
            "md": "markdown",
            "tex": "latex",
            "c++": "java/c/c++/c#",
            "cpp": "java/c/c++/c#",
            "csharp": "c#",
            "jinja2": "html",  # Map jinja2 templates to HTML
            "jinja": "html",  # Map jinja templates to HTML
            "j2": "html",  # Map j2 templates to HTML
            "django": "html",  # Map django templates to HTML
            "handlebars": "html",  # Map handlebars templates to HTML
            "mustache": "html",  # Map mustache templates to HTML
            "twig": "html",  # Map twig templates to HTML
            "liquid": "html",  # Map liquid templates to HTML
            "vue": "html",  # Map vue templates to HTML
            "svelte": "html",  # Map svelte templates to HTML
            "jsx": "javascript",  # Map JSX to JavaScript
            "tsx": "typescript",  # Map TSX to TypeScript
            "ps1": "powershell",  # Map PowerShell scripts
            "psm1": "powershell",  # Map PowerShell modules
            "bat": "shell",  # Map batch files to shell
            "cmd": "shell",  # Map command files to shell
            "zsh": "shell",  # Map zsh to shell
            "fish": "shell",  # Map fish to shell
        }

        if isinstance(code_element, Tag):
            classes = code_element.get("class")
            if classes:
                for cls in classes:
                    if cls.startswith("language-"):
                        # Convert language identifier to Notion's format
                        lang = cls.replace("language-", "").lower()
                        mapped_lang = language_map.get(lang, lang)

                        # Validate that the language is supported by Notion
                        if mapped_lang in notion_supported_languages:
                            language = mapped_lang
                        else:
                            logger.warning(
                                f"Unsupported language '{lang}' (mapped to '{mapped_lang}'), using 'plain text'"
                            )
                            language = "plain text"
                        break

        # Get code content and truncate if necessary
        code_content = code_element.get_text() if isinstance(code_element, Tag) else str(code_element)
        truncated_content = truncate_text_content(code_content.strip())

        return {
            "object": "block",
            "type": "code",
            "code": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": truncated_content},
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
            TitleBlockConverter(),
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


def validate_and_fix_blocks(blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validate and fix blocks to ensure they meet Notion's limits."""
    fixed_blocks = []

    for block in blocks:
        if block.get("type") == "table":
            # Fix table blocks by truncating cell content
            table_data = block.get("table", {})
            children = table_data.get("children", [])

            for row in children:
                if row.get("type") == "table_row":
                    cells = row.get("table_row", {}).get("cells", [])
                    for cell in cells:
                        for rich_text in cell:
                            if rich_text.get("type") == "text":
                                content = rich_text.get("text", {}).get("content", "")
                                if len(content) > NOTION_MAX_TEXT_LENGTH:
                                    truncated = truncate_text_content(content)
                                    rich_text["text"]["content"] = truncated
                                    logger.warning(
                                        f"Truncated table cell content from {len(content)} to"
                                        f" {len(truncated)} characters"
                                    )

        fixed_blocks.append(block)

    return fixed_blocks


def convert_html_to_blocks(html_content: str) -> List[Dict[str, Any]]:  # noqa: C901
    """Convert HTML content to Notion blocks.

    Args:
        html_content: HTML string to convert

    Returns:
        List[Dict[str, Any]]: List of Notion blocks
    """
    print(f"🔍 DEBUG: convert_html_to_blocks called with {len(html_content)} chars")
    logger.error(f"🔍 LOGGER DEBUG: convert_html_to_blocks called with {len(html_content)} chars")
    soup = BeautifulSoup(html_content, "html.parser")
    blocks: List[Dict[str, Any]] = []
    factory = BlockFactory()

    # Find the main content area or use the body
    main_content = soup.find("body") or soup

    # Process elements to avoid duplicates
    if not isinstance(main_content, Tag):
        return []

    for element in main_content.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "table", "pre"], recursive=True):
        # Check if we've hit the block limit
        if len(blocks) >= NOTION_MAX_BLOCKS_PER_PAGE:
            logger.warning(
                f"Reached Notion's maximum of {NOTION_MAX_BLOCKS_PER_PAGE} blocks per page. Remaining content will be"
                " truncated."
            )
            break

        # Special handling for tables - check if it's a code highlighting table first
        if element.name == "table":
            table_converter = TableConverter()
            classes = element.get("class", [])
            logger.info(f"Processing table with classes: {classes}")
            if table_converter._is_code_highlight_table(element):
                logger.info("Converting code highlighting table to code block")
                block = table_converter._convert_code_table_to_code_block(element)
                if block:
                    blocks.append(block)
                    logger.info("Added code block from highlighting table")
                continue
            else:
                logger.info("Processing table as regular table")

        # For pre tags, only process if they contain code
        if element.name == "pre" and not element.find("code"):
            continue
        # For standalone code blocks not in pre tags
        if element.name != "pre":
            code_elements = element.find_all("code", recursive=False)
            if code_elements:
                for code in code_elements:
                    if len(blocks) >= NOTION_MAX_BLOCKS_PER_PAGE:
                        break
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

    logger.info(f"Created {len(blocks)} blocks total (max allowed: {NOTION_MAX_BLOCKS_PER_PAGE})")

    # Final validation and fixing of all blocks
    fixed_blocks = validate_and_fix_blocks(blocks)
    logger.info(f"Validated and fixed {len(fixed_blocks)} blocks")

    return fixed_blocks
