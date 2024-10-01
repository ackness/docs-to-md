import asyncio
import logging

import click
from docs_to_md.parser import parse_readthedocs
from docs_to_md.utils import extract_project_name_from_url

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("D2M")


@click.command()
@click.option("--url", "-u", type=str, help="Root url of the readthedocs project")
@click.option(
    "--project-name",
    "-p",
    default="default",
    type=str,
    help="Name of the project",
)
@click.option(
    "--target-path",
    "-t",
    default="saved",
    type=str,
    help="Path to save the html and md files",
)
@click.option(
    "--no_jina",
    "-nj",
    is_flag=True,
    help="Use open-based api (default: ollama reader-lm) to parse html to markdown, if true, --token is required, and will ignore --api and --model",
)
@click.option(
    "--api",
    default="http://localhost:11434/v1",
    type=str,
    help="Base url of the openai/jina api, only works when --no_jina is false",
)
@click.option(
    "--token",
    default="ollama",
    type=str,
    help="Api key of the openai/jina api",
)
@click.option(
    "--model",
    default="reader-lm",
    type=str,
    help="Model to use for parsing html to markdown",
)
def main(
    url: str,
    project_name: str,
    target_path: str,
    no_jina: bool,
    api: str,
    token: str,
    model: str,
):
    if not url:
        logger.error("URL is required, use -u <url>")
        return
    if project_name == "default":
        project_name = extract_project_name_from_url(url)

    asyncio.run(
        parse_readthedocs(url, project_name, target_path, no_jina, api, token, model),
    )


if __name__ == "__main__":
    main()
