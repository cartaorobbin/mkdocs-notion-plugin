"""Tests for the notion-deploy command."""

from click.testing import CliRunner

from mkdocs_notion_plugin.commands import notion_deploy


def test_notion_deploy_command_exists():
    """Test that the notion-deploy command can be imported."""
    assert notion_deploy is not None
    assert callable(notion_deploy)


def test_notion_deploy_command_help():
    """Test that the notion-deploy command shows help."""
    runner = CliRunner()
    result = runner.invoke(notion_deploy, ["--help"])

    assert result.exit_code == 0
    assert "Deploy MkDocs documentation to Notion" in result.output
    assert "--config-file" in result.output
    assert "--verbose" in result.output
    assert "--quiet" in result.output


def test_notion_deploy_command_without_config():
    """Test that the command fails gracefully without a valid config."""
    runner = CliRunner()

    # Create a temporary directory without mkdocs.yml
    with runner.isolated_filesystem():
        result = runner.invoke(notion_deploy)

        # Should fail because no mkdocs.yml exists
        assert result.exit_code != 0
