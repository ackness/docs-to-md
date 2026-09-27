import respx
from typer.testing import CliRunner

from docs_to_md.cli import app

from .conftest import INDEX_HTML, INDEX_URL, PAGE_HTML_TEMPLATE

runner = CliRunner()


def test_cli_help_lists_command():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "readthedocs" in result.output


def test_cli_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert result.output.strip()


def test_cli_readthedocs_local(tmp_path):
    with respx.mock:
        respx.get(INDEX_URL).respond(200, text=INDEX_HTML)
        respx.get(url__regex=r"\.html$").respond(
            200,
            text=PAGE_HTML_TEMPLATE.format(title="P"),
        )
        result = runner.invoke(
            app,
            ["readthedocs", INDEX_URL, "-o", str(tmp_path)],
        )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "example" / "index.md").exists()


def test_cli_readthedocs_failure_exit_code(tmp_path):
    with respx.mock:
        respx.get(INDEX_URL).respond(200, text=INDEX_HTML)
        respx.get(url__regex=r"\.html$").respond(500)
        result = runner.invoke(
            app,
            ["readthedocs", INDEX_URL, "-o", str(tmp_path), "--retries", "0"],
        )
    assert result.exit_code == 1
    assert "1/3 pages" in result.output
