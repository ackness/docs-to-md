from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from lxml import html as lxml_html

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)

RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
RETRYABLE_ERRORS = (httpx.TimeoutException, httpx.TransportError)


async def request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    retries: int = 3,
    base_delay: float = 1.0,
    **kwargs,
) -> httpx.Response:
    """Send a request, retrying on 429/5xx and transient network errors.

    Honors the ``Retry-After`` response header when present, otherwise uses
    exponential backoff. Raises the last ``httpx`` error on exhaustion.
    """
    delay = base_delay
    for attempt in range(retries + 1):
        try:
            response = await client.request(method, url, **kwargs)
        except RETRYABLE_ERRORS:
            if attempt >= retries:
                raise
            await asyncio.sleep(delay)
            delay *= 2
            continue

        if response.status_code in RETRYABLE_STATUS and attempt < retries:
            retry_after = response.headers.get("retry-after")
            wait = float(retry_after) if retry_after else delay
            logger.warning(
                "%s %s -> %s, retrying in %.1fs (%d/%d)",
                method,
                url,
                response.status_code,
                wait,
                attempt + 1,
                retries,
            )
            await asyncio.sleep(wait)
            delay *= 2
            continue

        response.raise_for_status()
        return response

    raise RuntimeError("unreachable")


async def fetch_text(client: httpx.AsyncClient, url: str, *, retries: int = 3) -> str:
    """Fetch a URL and return its body text, with retries."""
    response = await request_with_retry(client, "GET", url, retries=retries)
    return response.text


def normalize_index_url(url: str) -> str:
    """Strip a trailing ``*.html`` filename so the URL is the docs root."""
    url = url.split("#", 1)[0].split("?", 1)[0]
    url = re.sub(r"/[^/]+\.html$", "", url)
    return url if url.endswith("/") else url + "/"


def extract_project_name_from_url(url: str) -> str:
    """Derive a filesystem-friendly project name from a docs URL."""
    parsed = urlparse(url)
    host = parsed.hostname or "docs"
    if host.endswith("readthedocs.io") or "readthedocs" in host:
        return host.split(".")[0]
    # Custom domain: prefer the first path segment (e.g. docs.python.org/3/ -> "3"),
    # otherwise fall back to the second-level domain label.
    segment = next((s for s in parsed.path.split("/") if s), None)
    if segment:
        return segment
    parts = host.split(".")
    return parts[-2] if len(parts) >= 2 else parts[0]


def _page_name(index_url: str, url: str) -> str:
    relative = url.removeprefix(index_url).strip("/")
    relative = re.sub(r"\.html$", "", relative)
    name = re.sub(r"[^0-9A-Za-z._-]+", "_", relative).strip("_")
    return name or "index"


def discover_sub_urls(index_url: str, index_html: str) -> dict[str, str]:
    """Extract the table-of-contents links of a Sphinx/ReadTheDocs index page.

    Returns a mapping of ``{page_name: absolute_url}``; the index page itself
    is included under the name ``"index"``.
    """
    tree = lxml_html.fromstring(index_html)
    hrefs = tree.xpath('//a[contains(@class, "reference internal")]/@href')
    base = urlparse(index_url)
    pages: dict[str, str] = {}
    for href in hrefs:
        url = urljoin(index_url, href).split("#", 1)[0]
        parsed = urlparse(url)
        if parsed.netloc != base.netloc or not url.endswith(".html"):
            continue
        pages.setdefault(_page_name(index_url, url), url)
    pages.setdefault("index", index_url)
    return pages


def preprocess_html(content: str) -> str:
    """Reduce a documentation page to its article body, minus noise.

    Removes scripts, styles, images, navigation and presentational
    attributes so downstream converters see only the content.
    """
    tree = lxml_html.fromstring(content)

    for element in tree.xpath("//script | //style | //noscript | //img"):
        element.getparent().remove(element)
    # Sphinx "permalink to this heading" anchors render as noise in Markdown
    for element in tree.xpath('//a[contains(@class, "headerlink")]'):
        element.getparent().remove(element)
    for element in tree.xpath("//*[@role='navigation' or @role='banner' or @role='contentinfo']"):
        element.getparent().remove(element)
    for element in tree.xpath("//*[@class or @id]"):
        element.attrib.pop("class", None)
        element.attrib.pop("id", None)

    for query in (
        "//*[@itemprop='articleBody']",
        "//*[@role='main']",
        "//main",
        "//article",
        "//body",
    ):
        matches = tree.xpath(query)
        if matches:
            body = matches[0]
            break
    else:
        body = tree

    cleaned = lxml_html.tostring(body, encoding="unicode")
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n\s*\n+", "\n\n", cleaned)
    return cleaned.strip()


def save_text(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def page_file_stem(name: str) -> str:
    return re.sub(r"[^0-9A-Za-z._-]+", "_", name) or "index"
