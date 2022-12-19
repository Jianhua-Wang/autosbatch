"""tests for cli.py."""

from typer.testing import CliRunner

from autosbatch.cli import app


def test_command_line_interface():
    """Test the CLI."""
    runner = CliRunner()
    result = runner.invoke(app)
    assert result.exit_code == 0
    assert "main" in result.stdout
    help_result = runner.invoke(app, ["--help"])
    assert help_result.exit_code == 0
    assert "Show this message and exit." in help_result.stdout


def test_single_job():
    """Test single_job."""
    runner = CliRunner()
    result = runner.invoke(app, ["single-job", "--help"])
    assert result.exit_code == 0
    assert "Show this message and exit." in result.stdout


def test_multi_job():
    """Test multi_job."""
    runner = CliRunner()
    result = runner.invoke(app, ["multi-job", "--help"])
    assert result.exit_code == 0
    assert "Show this message" in result.stdout


def test_clean():
    """Test clean."""
    runner = CliRunner()
    result = runner.invoke(app, ["clean", "--help"])
    assert result.exit_code == 0
    assert "Show this message and exit." in result.stdout
