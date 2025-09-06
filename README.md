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
      parent_page_id: your-parent-page-id
      version: your-version
      cache_dir: .notion_cache  # optional
      deploy_on_build: false  # optional
```

### Required Configuration

- `notion_token`: Your Notion integration token. Create one at https://www.notion.so/my-integrations
- `parent_page_id`: The ID of the Notion page where your documentation will be deployed
- `version`: Version identifier for your documentation

### Optional Configuration

- `cache_dir`: Directory to store cached Notion content (default: `.notion_cache`)
- `deploy_on_build`: Whether to automatically deploy to Notion during build (default: `false`)

## Usage

1. Create a Notion integration and get your token
2. Share your Notion database with the integration
3. Configure the plugin in your `mkdocs.yml`
4. Deploy your documentation using one of these methods:

### Method 1: Manual Deployment (Recommended)

Build and deploy separately for better control:

```bash
# Build your documentation
mkdocs build

# Deploy to Notion
mkdocs notion-deploy

# Or if using Poetry for development
poetry run mkdocs notion-deploy
```

### Method 2: Automatic Deployment

Enable automatic deployment during build by adding `deploy_on_build: true` to your configuration:

```yaml
plugins:
  - notion:
      notion_token: your-notion-integration-token
      parent_page_id: your-parent-page-id
      version: your-version
      deploy_on_build: true  # Enable automatic deployment
```

Then simply run:

```bash
mkdocs build
```

### Command Options

The notion-deploy command supports several options:

```bash
mkdocs notion-deploy --help

Options:
  -f, --config-file FILE  Provide a specific MkDocs config file
  -s, --strict            Enable strict mode (abort on warnings)
  -v, --verbose           Enable verbose output
  -q, --quiet             Silence warnings
  --clean / --dirty       Remove old files before building (default: clean)
```

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