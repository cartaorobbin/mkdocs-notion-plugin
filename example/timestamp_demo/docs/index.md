# MkDocs Notion Plugin

Welcome to the MkDocs Notion Plugin documentation! This plugin enables seamless integration between MkDocs and Notion, allowing you to automatically publish your documentation to Notion pages.

## Features

- **Automatic Synchronization**: Automatically publishes your MkDocs documentation to Notion when you build your site
- **Smart Content Conversion**: Intelligently converts HTML content to Notion blocks
- **Hierarchical Structure**: Maintains your documentation's structure in Notion
- **Selective Publishing**: Intelligently skips utility pages like 404 and search

## Quick Start

### Installation

Install the plugin using pip:

```bash
pip install mkdocs-notion-plugin
```

Or if you're using Poetry:

```bash
poetry add mkdocs-notion-plugin
```

### Configuration

Add the plugin to your `mkdocs.yml`:

```yaml
plugins:
  - notion:
      notion_token: your-notion-token
      database_id: your-database-id
      parent_page_id: your-parent-page-id
```

## How It Works

The plugin processes your documentation in the following steps:

1. **Build Phase**: When you run `mkdocs build`, your documentation is first converted to HTML
2. **Processing**: The plugin then:
   - Creates a root page in Notion
   - Processes each HTML file
   - Converts content to Notion blocks
   - Maintains the hierarchy

### Supported Elements

The plugin currently supports the following Markdown elements:

| Element | Notion Block Type |
|---------|------------------|
| Headings (h1) | heading_1 |
| Headings (h2) | heading_2 |
| Paragraphs | paragraph |
| Code blocks | code |
| Lists | bulleted_list_item/numbered_list_item |

## Tips and Best Practices

> **Note**: Always ensure you have the necessary Notion API permissions before running the plugin.

### Security Considerations

1. Keep your Notion token secure
2. Use environment variables for sensitive information
3. Regularly rotate your API keys

## Contributing

We welcome contributions! Here's how you can help:

- Report bugs by opening issues
- Submit pull requests for bug fixes or new features
- Improve documentation
- Share your use cases and feedback

## License

This project is licensed under the MIT License - see the LICENSE file for details.
