#!/usr/bin/env python3
"""Enhanced MkDocs CLI with notion-deploy command."""

from mkdocs.__main__ import cli

from .commands import notion_deploy

# Add our command to MkDocs CLI
cli.add_command(notion_deploy)

if __name__ == "__main__":
    cli()
