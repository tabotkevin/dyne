from unittest.mock import patch

from click.testing import CliRunner

from dyne.cli import cli


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "2.0.4" in result.output


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Enable debug mode." in result.output


def test_run_command_params():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert "--host" in result.output
    assert "--port" in result.output


@patch("uvicorn.run")
def test_run_calls_uvicorn(mock_run):
    runner = CliRunner()
    runner.invoke(cli, ["--app", "myapp:app", "--port", "9000", "run"])

    args, kwargs = mock_run.call_args
    assert args[0] == "myapp:app"
    assert kwargs["port"] == 9000
