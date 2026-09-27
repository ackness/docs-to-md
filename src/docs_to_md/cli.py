from __future__ import annotations

import asyncio
import logging
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer
from rich.logging import RichHandler
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn

from docs_to_md.engines import DEFAULT_OPENAI_BASE_URL, DEFAULT_OPENAI_MODEL, make_converter
from docs_to_md.pipeline import convert_readthedocs

app = typer.Typer(
    name="d2m",
    help="Convert documentation sites to Markdown.",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)


class Engine(StrEnum):
    local = "local"
    jina = "jina"
    openai = "openai"


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
    )


@app.command()
def readthedocs(
    url: Annotated[str, typer.Argument(help="Root URL of the documentation project.")],
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", "-o", help="Directory the <project>/ output is written to."),
    ] = Path("output"),
    name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="Project name (default: derived from the URL)."),
    ] = None,
    engine: Annotated[
        Engine,
        typer.Option(
            "--engine",
            "-e",
            help="HTML->Markdown engine: local (offline, default), "
            "jina (Jina Reader API) or openai (OpenAI-compatible API, e.g. Ollama).",
        ),
    ] = Engine.local,
    api_key: Annotated[
        str | None,
        typer.Option(
            "--api-key",
            "-k",
            envvar=["JINA_API_KEY", "OPENAI_API_KEY", "D2M_API_KEY"],
            help="API key for the jina/openai engines. "
            "Also read from JINA_API_KEY / OPENAI_API_KEY / D2M_API_KEY.",
        ),
    ] = None,
    api_base: Annotated[
        str,
        typer.Option("--api-base", help="Base URL of the OpenAI-compatible API."),
    ] = DEFAULT_OPENAI_BASE_URL,
    model: Annotated[
        str,
        typer.Option("--model", "-m", help="Model for the openai engine."),
    ] = DEFAULT_OPENAI_MODEL,
    concurrency: Annotated[
        int,
        typer.Option("--concurrency", "-c", min=1, help="Max parallel requests."),
    ] = 4,
    request_timeout: Annotated[
        float,
        typer.Option("--timeout", help="Per-request timeout in seconds."),
    ] = 30.0,
    retries: Annotated[
        int,
        typer.Option("--retries", min=0, help="Retries per request on 429/5xx/network errors."),
    ] = 3,
    save_html: Annotated[
        bool,
        typer.Option("--save-html", help="Also keep the downloaded HTML under html/."),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Debug logging."),
    ] = False,
) -> None:
    """Convert a ReadTheDocs/Sphinx documentation site to Markdown."""
    _configure_logging(verbose)
    converter = make_converter(
        engine.value,
        api_key=api_key,
        base_url=api_base,
        model=model,
        retries=retries,
    )

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
    )
    task_id = progress.add_task("Converting pages", total=None)

    def on_progress(done: int, total: int) -> None:
        progress.update(task_id, total=total, completed=done)

    with progress:
        try:
            result = asyncio.run(
                convert_readthedocs(
                    url,
                    converter=converter,
                    output_dir=output_dir,
                    project_name=name,
                    concurrency=concurrency,
                    request_timeout=request_timeout,
                    retries=retries,
                    save_html=save_html,
                    on_progress=on_progress,
                )
            )
        except Exception as exc:
            if verbose:
                raise
            typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1) from exc

    for page in result.failed:
        typer.secho(f"  failed: {page.url} ({page.error})", fg=typer.colors.RED, err=True)

    typer.echo(
        f"{len(result.succeeded)}/{len(result.pages)} pages -> {result.output_dir.resolve()}"
    )
    if result.failed:
        raise typer.Exit(code=1)


@app.command()
def version() -> None:
    """Print the package version."""
    from docs_to_md import __version__

    typer.echo(__version__)


if __name__ == "__main__":
    app()
