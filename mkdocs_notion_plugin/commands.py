"""MkDocs Notion Plugin Commands."""

import logging
from typing import Optional

import click
from mkdocs.__main__ import cli
from mkdocs.commands.build import build
from mkdocs.config import load_config

from .plugin import NotionPlugin

logger = logging.getLogger("mkdocs.commands.notion")


@click.command()
@click.option(
    "-f",
    "--config-file",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Provide a specific MkDocs config file.",
)
@click.option(
    "-s",
    "--strict",
    is_flag=True,
    help="Enable strict mode. This will cause MkDocs to abort the build on any warnings.",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enable verbose output.",
)
@click.option(
    "-q",
    "--quiet",
    is_flag=True,
    help="Silence warnings.",
)
@click.option(
    "--clean/--dirty",
    default=True,
    help="Whether to remove old files from the site_dir before building (the default).",
)
@click.pass_context
def notion_deploy(
    ctx: click.Context,
    config_file: Optional[str] = None,
    strict: bool = False,
    verbose: bool = False,
    quiet: bool = False,
    clean: bool = True,
) -> None:
    """Deploy MkDocs documentation to Notion.

    This command builds the documentation and then deploys it to Notion
    using the configured Notion plugin settings.
    """
    # Configure logging
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    elif quiet:
        logging.basicConfig(level=logging.ERROR)
    else:
        logging.basicConfig(level=logging.INFO)

    try:
        # Load MkDocs configuration
        config = load_config(config_file=config_file, strict=strict)

        # Check if notion plugin is configured
        notion_plugin = None
        for plugin_name, plugin_instance in config.plugins.items():
            if plugin_name == "notion" or isinstance(plugin_instance, NotionPlugin):
                notion_plugin = plugin_instance
                break

        if not notion_plugin:
            click.echo("Error: Notion plugin is not configured in mkdocs.yml", err=True)
            click.echo("Please add the notion plugin to your mkdocs.yml configuration:", err=True)
            click.echo("plugins:", err=True)
            click.echo("  - notion:", err=True)
            click.echo("      notion_token: your-token", err=True)
            click.echo("      parent_page_id: your-page-id", err=True)
            click.echo("      version: your-version", err=True)
            raise click.Abort()

        # Build the documentation first
        click.echo("Building documentation...")
        build(config, dirty=not clean)

        # Deploy to Notion
        click.echo("Deploying to Notion...")

        # Call the deployment logic from the plugin directly
        # The plugin will initialize the Notion client when needed
        notion_plugin.deploy_to_notion(config)

        click.echo("✅ Successfully deployed documentation to Notion!")

    except Exception as e:
        click.echo(f"❌ Error during deployment: {e}", err=True)
        raise click.Abort() from e


# Add our command to MkDocs CLI and create the enhanced CLI
cli.add_command(notion_deploy)


def mkdocs_with_notion() -> None:
    """Enhanced MkDocs CLI with notion-deploy command."""
    cli()
