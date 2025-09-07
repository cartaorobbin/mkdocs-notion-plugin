"""Tests for the blocks module."""

from bs4 import BeautifulSoup

from mkdocs_notion_plugin.blocks import (
    BlockConverter,
    BlockFactory,
    CodeBlockConverter,
    HeadingConverter,
    ParagraphConverter,
    TableConverter,
    convert_html_to_blocks,
)


def create_soup(html: str) -> BeautifulSoup:
    """Create a BeautifulSoup object from HTML string."""
    return BeautifulSoup(html, "html.parser")


def test_heading_converter():
    """Test heading block conversion."""
    converter = HeadingConverter()

    # Test h1-h6 conversion
    for i in range(1, 7):
        html = f"<h{i}>Test Heading {i}</h{i}>"
        element = create_soup(html).find(f"h{i}")

        assert converter.can_convert(element)
        block = converter.convert(element)

        assert block is not None
        assert block["object"] == "block"
        # Notion only supports h1-h3, so h4-h6 should be converted to h3
        expected_level = min(i, 3)
        assert block["type"] == f"heading_{expected_level}"
        assert block[f"heading_{expected_level}"]["rich_text"][0]["text"]["content"] == f"Test Heading {i}"


def test_paragraph_converter():
    """Test paragraph block conversion."""
    converter = ParagraphConverter()
    html = "<p>Test paragraph content</p>"
    element = create_soup(html).find("p")

    assert converter.can_convert(element)
    block = converter.convert(element)

    assert block is not None
    assert block["object"] == "block"
    assert block["type"] == "paragraph"
    assert block["paragraph"]["rich_text"][0]["text"]["content"] == "Test paragraph content"


def test_table_converter():
    """Test table block conversion."""
    converter = TableConverter()

    # Test table with headers
    html = """
    <table>
        <thead>
            <tr><th>Header 1</th><th>Header 2</th></tr>
        </thead>
        <tbody>
            <tr><td>Row 1 Col 1</td><td>Row 1 Col 2</td></tr>
            <tr><td>Row 2 Col 1</td><td>Row 2 Col 2</td></tr>
        </tbody>
    </table>
    """
    element = create_soup(html).find("table")

    assert converter.can_convert(element)
    block = converter.convert(element)

    assert block is not None
    assert block["object"] == "block"
    assert block["type"] == "table"
    assert block["table"]["has_column_header"] is True
    assert block["table"]["table_width"] == 2

    # Check headers
    header_row = block["table"]["children"][0]
    assert header_row["type"] == "table_row"
    assert header_row["table_row"]["cells"][0][0]["text"]["content"] == "Header 1"
    assert header_row["table_row"]["cells"][1][0]["text"]["content"] == "Header 2"

    # Check data rows
    data_rows = block["table"]["children"][1:]
    assert len(data_rows) == 2
    assert data_rows[0]["table_row"]["cells"][0][0]["text"]["content"] == "Row 1 Col 1"
    assert data_rows[1]["table_row"]["cells"][1][0]["text"]["content"] == "Row 2 Col 2"


def test_code_block_converter():
    """Test code block conversion."""
    converter = CodeBlockConverter()

    # Test code block with language
    html = '<pre><code class="language-python">def test():\n    pass</code></pre>'
    element = create_soup(html).find("pre")

    assert converter.can_convert(element)
    block = converter.convert(element)

    assert block is not None
    assert block["object"] == "block"
    assert block["type"] == "code"
    assert block["code"]["language"] == "python"
    assert block["code"]["rich_text"][0]["text"]["content"] == "def test():\n    pass"

    # Test code block without language
    html = "<code>plain text code</code>"
    element = create_soup(html).find("code")

    assert converter.can_convert(element)
    block = converter.convert(element)

    assert block["code"]["language"] == "plain text"


def test_code_block_language_validation():
    """Test that unsupported languages are mapped to supported ones or 'plain text'."""
    converter = CodeBlockConverter()

    # Test jinja2 template mapping to HTML
    html = '<pre><code class="language-jinja2">{{ variable }}</code></pre>'
    element = create_soup(html).find("pre")
    block = converter.convert(element)
    assert block["code"]["language"] == "html"

    # Test JavaScript mapping
    html = '<pre><code class="language-js">console.log("test");</code></pre>'
    element = create_soup(html).find("pre")
    block = converter.convert(element)
    assert block["code"]["language"] == "javascript"

    # Test unsupported language fallback to plain text
    html = '<pre><code class="language-unsupported">some code</code></pre>'
    element = create_soup(html).find("pre")
    block = converter.convert(element)
    assert block["code"]["language"] == "plain text"

    # Test case insensitive mapping
    html = '<pre><code class="language-PYTHON">def test(): pass</code></pre>'
    element = create_soup(html).find("pre")
    block = converter.convert(element)
    assert block["code"]["language"] == "python"


def test_table_code_highlight_language_validation():
    """Test that code highlighting tables also validate languages properly."""
    converter = TableConverter()

    # Test jinja2 code highlighting table
    html = """
    <table class="highlighttable">
        <tr>
            <td class="code">
                <div class="highlight">
                    <pre><code class="language-jinja2">{{ variable }}</code></pre>
                </div>
            </td>
        </tr>
    </table>
    """
    element = create_soup(html).find("table")

    assert converter.can_convert(element)
    block = converter.convert(element)

    # Should be converted to code block with validated language
    assert block is not None
    assert block["type"] == "code"
    assert block["code"]["language"] == "html"  # jinja2 mapped to html

    # Test unsupported language in code highlighting table
    html = """
    <table class="highlighttable">
        <tr>
            <td class="code">
                <div class="highlight">
                    <pre><code class="language-unsupported">some code</code></pre>
                </div>
            </td>
        </tr>
    </table>
    """
    element = create_soup(html).find("table")
    block = converter.convert(element)

    assert block["type"] == "code"
    assert block["code"]["language"] == "plain text"  # fallback to plain text


def test_block_factory():
    """Test block factory converter selection."""
    factory = BlockFactory()

    # Test heading
    element = create_soup("<h1>Test</h1>").find("h1")
    converter = factory.get_converter(element)
    assert isinstance(converter, HeadingConverter)

    # Test paragraph
    element = create_soup("<p>Test</p>").find("p")
    converter = factory.get_converter(element)
    assert isinstance(converter, ParagraphConverter)

    # Test unknown element
    element = create_soup("<div>Test</div>").find("div")
    converter = factory.get_converter(element)
    assert converter is None


def test_convert_html_to_blocks():
    """Test the main conversion function."""
    html = """
    <div>
        <h1>Document Title</h1>
        <p>Introduction paragraph</p>
        <table>
            <tr><th>Header</th></tr>
            <tr><td>Data</td></tr>
        </table>
        <pre><code>Some code</code></pre>
    </div>
    """

    blocks = convert_html_to_blocks(html)

    assert len(blocks) == 4
    assert blocks[0]["type"] == "heading_1"
    assert blocks[1]["type"] == "paragraph"
    assert blocks[2]["type"] == "table"
    assert blocks[3]["type"] == "code"


def test_convert_empty_html():
    """Test conversion of empty or invalid HTML."""
    assert convert_html_to_blocks("") == []
    assert convert_html_to_blocks("<div></div>") == []


def test_custom_block_converter():
    """Test creating a custom block converter."""

    class QuoteConverter(BlockConverter):
        """Convert blockquote elements."""

        def can_convert(self, element):
            return element.name == "blockquote"

        def convert(self, element):
            return {
                "object": "block",
                "type": "quote",
                "quote": {"rich_text": [{"type": "text", "text": {"content": element.get_text()}}]},
            }

    # Create a factory with the custom converter
    factory = BlockFactory()
    factory.converters.append(QuoteConverter())

    # Test the custom converter
    html = "<blockquote>Test quote</blockquote>"
    element = create_soup(html).find("blockquote")
    converter = factory.get_converter(element)

    assert converter is not None
    block = converter.convert(element)
    assert block["type"] == "quote"
    assert block["quote"]["rich_text"][0]["text"]["content"] == "Test quote"
