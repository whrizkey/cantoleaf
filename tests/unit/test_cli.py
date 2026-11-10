from typer.testing import CliRunner

from cantoleaf.cli import app

runner = CliRunner()


def test_cli_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "CantoLeaf" in result.stdout
    assert "0.1.0" in result.stdout


def test_cli_doctor() -> None:
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "System Diagnostics" in result.stdout
    assert "Python Runtime" in result.stdout
