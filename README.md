# mkdocs-notion-plugin

[![Release](https://img.shields.io/github/v/release/cartaorobbin/mkdocs-notion-plugin)](https://github.com/cartaorobbin/mkdocs-notion-plugin/releases)
[![Build status](https://img.shields.io/github/actions/workflow/status/cartaorobbin/mkdocs-notion-plugin/main.yml?branch=main)](https://github.com/cartaorobbin/mkdocs-notion-plugin/actions/workflows/main.yml)
[![Python](https://img.shields.io/pypi/pyversions/mkdocs-notion-plugin)](https://pypi.org/project/mkdocs-notion-plugin/)
[![codecov](https://codecov.io/gh/cartaorobbin/mkdocs-notion-plugin/branch/main/graph/badge.svg)](https://codecov.io/gh/cartaorobbin/mkdocs-notion-plugin)
[![License](https://img.shields.io/github/license/cartaorobbin/mkdocs-notion-plugin)](https://github.com/cartaorobbin/mkdocs-notion-plugin/blob/main/LICENSE)

A MkDocs plugin that integrates Notion content into your documentation.

> ⚠️ **Development Phase Warning**
> 
> This project is currently in active development and **NOT ready for production use**. 
> Features may be incomplete, APIs may change without notice, and stability is not guaranteed.
> Use at your own risk and expect breaking changes between versions.
> 
> We welcome feedback and contributions, but please do not use this in production environments yet.

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
      # Notion configuration (only required for deployment)
      notion_token: your-notion-integration-token  # optional
      parent_page_id: your-parent-page-id          # optional
      version: your-version                        # optional
      cache_dir: .notion_cache                     # optional
      deploy_on_build: false                       # optional
```

### Configuration for Deployment

The following configuration is only required when using `mkdocs notion-deploy`:

- `notion_token`: Your Notion integration token. Create one at https://www.notion.so/my-integrations
- `parent_page_id`: The ID of the Notion page where your documentation will be deployed
- `version`: Version identifier for your documentation

### Optional Configuration

- `cache_dir`: Directory to store cached Notion content (default: `.notion_cache`)
- `deploy_on_build`: Whether to automatically deploy to Notion during build (default: `false`)

**Note**: You can use `mkdocs build` and `mkdocs serve` without any Notion configuration. The Notion settings are only validated when you run `mkdocs notion-deploy`.

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