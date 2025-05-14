# mkdocs-notion-plugin

[![Release](https://img.shields.io/github/v/release/tomas_correa/mkdocs-notion-plugin)](https://img.shields.io/github/v/release/tomas_correa/mkdocs-notion-plugin)
[![Build status](https://img.shields.io/github/actions/workflow/status/tomas_correa/mkdocs-notion-plugin/main.yml?branch=main)](https://github.com/tomas_correa/mkdocs-notion-plugin/actions/workflows/main.yml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/tomas_correa/mkdocs-notion-plugin/branch/main/graph/badge.svg)](https://codecov.io/gh/tomas_correa/mkdocs-notion-plugin)
[![Commit activity](https://img.shields.io/github/commit-activity/m/tomas_correa/mkdocs-notion-plugin)](https://img.shields.io/github/commit-activity/m/tomas_correa/mkdocs-notion-plugin)
[![License](https://img.shields.io/github/license/tomas_correa/mkdocs-notion-plugin)](https://img.shields.io/github/license/tomas_correa/mkdocs-notion-plugin)

A MkDocs plugin that integrates Notion content into your documentation.

## Features

- Fetch content from Notion databases
- Cache Notion content locally for faster builds
- Seamless integration with MkDocs

## Installation

```bash
pip install mkdocs-notion-plugin
```

## Configuration

Add the plugin to your `mkdocs.yml`:

```yaml
plugins:
  - notion:
      notion_token: your-notion-integration-token

      cache_dir: .notion_cache  # optional
```

### Required Configuration

- `notion_token`: Your Notion integration token. Create one at https://www.notion.so/my-integrations


### Optional Configuration

- `cache_dir`: Directory to store cached Notion content (default: `.notion_cache`)

## Usage

1. Create a Notion integration and get your token
2. Share your Notion database with the integration
3. Configure the plugin in your `mkdocs.yml`
4. Build your documentation

## Development

```bash
# Install dependencies
poetry install

# Run tests
poetry run pytest

# Format code
poetry run black .
```

## Links

- **Github repository**: <https://github.com/tomas_correa/mkdocs-notion-plugin/>
- **Documentation**: <https://tomas_correa.github.io/mkdocs-notion-plugin/>

## License

MIT License

---

Repository initiated with [fpgmaas/cookiecutter-poetry](https://github.com/fpgmaas/cookiecutter-poetry).

Change