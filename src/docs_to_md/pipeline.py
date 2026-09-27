from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from docs_to_md.engines import Converter, Page
from docs_to_md.utils import (
    USER_AGENT,
    discover_sub_urls,
    extract_project_name_from_url,
    fetch_text,
    normalize_index_url,
    page_file_stem,
    save_text,
)

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int], None]
"""Called after each page finishes: ``(completed_count, total_count)``."""


@dataclass
class PageResult:
    name: str
    url: str
    markdown_path: Path | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass
class ConvertResult:
    project_name: str
    output_dir: Path
    pages: list[PageResult] = field(default_factory=list)

    @property
    def succeeded(self) -> list[PageResult]:
        return [p for p in self.pages if p.ok]

    @property
    def failed(self) -> list[PageResult]:
        return [p for p in self.pages if not p.ok]


async def convert_readthedocs(
    root_url: str,
    *,
    converter: Converter,
    output_dir: str | Path = "output",
    project_name: str | None = None,
    concurrency: int = 4,
    request_timeout: float = 30.0,
    retries: int = 3,
    save_html: bool = False,
    on_progress: ProgressCallback | None = None,
) -> ConvertResult:
    """Convert a ReadTheDocs-style documentation site to Markdown files.

    Discovers the table-of-contents pages from ``root_url``, converts each
    page with ``converter`` and writes ``<output_dir>/<project>/<page>.md``.
    Failures on individual pages are collected in the result instead of
    aborting the whole run.
    """
    index_url = normalize_index_url(root_url)
    project = project_name or extract_project_name_from_url(index_url)
    target = Path(output_dir) / project
    result = ConvertResult(project_name=project, output_dir=target)

    semaphore = asyncio.Semaphore(concurrency)
    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)

    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        timeout=request_timeout,
        limits=limits,
        follow_redirects=True,
    ) as client:
        logger.info("Fetching index page %s", index_url)
        index_html = await fetch_text(client, index_url, retries=retries)
        sub_urls = discover_sub_urls(index_url, index_html)
        logger.info("Discovered %d pages under %s", len(sub_urls), index_url)

        pages = [Page(name, url) for name, url in sub_urls.items()]
        by_name = {p.name: p for p in pages}
        by_name["index"].html = index_html

        if converter.needs_html:
            await _fill_html(client, pages, semaphore, retries)
        elif save_html:
            logger.info("--save-html needs page markup; downloading it despite %s", converter.name)
            await _fill_html(client, pages, semaphore, retries)

        total = len(pages)
        done = 0

        async def handle(page: Page) -> PageResult:
            nonlocal done
            try:
                if converter.needs_html and not page.html:
                    raise RuntimeError("could not download page HTML")
                if save_html and page.html:
                    save_text(target / "html" / f"{page_file_stem(page.name)}.html", page.html)
                markdown = await converter.convert(client, page)
                path = save_text(target / f"{page_file_stem(page.name)}.md", markdown)
                return PageResult(page.name, page.url, markdown_path=path)
            except Exception as exc:
                logger.error("Failed to convert %s: %s", page.url, exc)
                return PageResult(page.name, page.url, error=str(exc))
            finally:
                done += 1
                if on_progress:
                    on_progress(done, total)

        async def guarded(page: Page) -> PageResult:
            async with semaphore:
                return await handle(page)

        result.pages = list(await asyncio.gather(*(guarded(p) for p in pages)))

    result.pages.sort(key=lambda p: p.name)
    logger.info(
        "Done: %d/%d pages written to %s",
        len(result.succeeded),
        len(result.pages),
        target,
    )
    return result


async def _fill_html(
    client: httpx.AsyncClient,
    pages: list[Page],
    semaphore: asyncio.Semaphore,
    retries: int,
) -> None:
    """Download the HTML for every page that doesn't have it yet."""

    async def fetch_one(page: Page) -> None:
        if page.html is not None:
            return
        async with semaphore:
            try:
                page.html = await fetch_text(client, page.url, retries=retries)
            except httpx.HTTPError as exc:
                logger.error("Failed to fetch %s: %s", page.url, exc)
                page.html = ""

    await asyncio.gather(*(fetch_one(p) for p in pages))
