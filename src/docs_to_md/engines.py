from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

import httpx
import openai
from markdownify import markdownify

from docs_to_md.utils import preprocess_html, request_with_retry

logger = logging.getLogger(__name__)

JINA_READER_API = "https://r.jina.ai"
DEFAULT_OPENAI_BASE_URL = "http://localhost:11434/v1"
DEFAULT_OPENAI_MODEL = "reader-lm"

OPENAI_SYSTEM_PROMPT = (
    "You are a precise HTML-to-Markdown converter. "
    "Convert the HTML document the user sends into clean Markdown. "
    "Preserve the heading hierarchy, code blocks, tables, lists and links. "
    "Drop navigation menus, sidebars, footers and other chrome. "
    "Reply with Markdown only — no preamble, no commentary, no fenced "
    "wrapper around the whole document."
)


@dataclass
class Page:
    """A documentation page to convert.

    ``html`` is only populated when the selected converter has
    ``needs_html = True`` (i.e. it converts markup we fetched ourselves).
    """

    name: str
    url: str
    html: str | None = None


class Converter(Protocol):
    """Engine that turns a documentation page into Markdown."""

    name: str
    #: Whether the pipeline must download each page's HTML for this engine.
    needs_html: bool

    async def convert(self, client: httpx.AsyncClient, page: Page) -> str:
        """Return the Markdown for ``page``, or raise on failure."""
        ...


@dataclass
class LocalConverter:
    """Offline HTML -> Markdown via ``markdownify`` (no external service)."""

    name: str = "local"
    needs_html: bool = True

    async def convert(self, client: httpx.AsyncClient, page: Page) -> str:
        assert page.html is not None
        return markdownify(preprocess_html(page.html), heading_style="ATX").strip()


@dataclass
class OpenAIConverter:
    """HTML -> Markdown through any OpenAI-compatible chat API.

    Works with Ollama (e.g. ``reader-lm``), OpenAI itself, vLLM, etc.
    """

    base_url: str = DEFAULT_OPENAI_BASE_URL
    api_key: str = "ollama"
    model: str = DEFAULT_OPENAI_MODEL
    retries: int = 3
    client: openai.AsyncOpenAI | None = None
    name: str = "openai"
    needs_html: bool = True

    def _client(self) -> openai.AsyncOpenAI:
        if self.client is None:
            self.client = openai.AsyncOpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                max_retries=self.retries,
            )
        return self.client

    async def convert(self, client: httpx.AsyncClient, page: Page) -> str:
        assert page.html is not None
        ai = self._client()
        try:
            response = await ai.chat.completions.create(
                model=self.model,
                stream=False,
                messages=[
                    {"role": "system", "content": OPENAI_SYSTEM_PROMPT},
                    {"role": "user", "content": preprocess_html(page.html)},
                ],
            )
        except Exception as exc:  # openai raises a broad hierarchy
            raise RuntimeError(f"OpenAI-compatible API at {self.base_url} failed: {exc}") from exc
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError(f"Empty response from model {self.model!r}")
        return content.strip()


@dataclass
class JinaConverter:
    """URL -> Markdown via the hosted Jina Reader API (``r.jina.ai``).

    Jina fetches and renders the page itself, so the pipeline does not
    need to download sub-page HTML when this engine is selected.
    """

    api_key: str | None = None
    retries: int = 3
    name: str = "jina"
    needs_html: bool = False

    async def convert(self, client: httpx.AsyncClient, page: Page) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        response = await request_with_retry(
            client,
            "POST",
            JINA_READER_API,
            headers=headers,
            json={"url": page.url},
            retries=self.retries,
        )
        return response.text.strip()


def make_converter(
    engine: str,
    *,
    api_key: str | None = None,
    base_url: str = DEFAULT_OPENAI_BASE_URL,
    model: str = DEFAULT_OPENAI_MODEL,
    retries: int = 3,
) -> Converter:
    """Build a converter by name: ``local``, ``jina`` or ``openai``."""
    if engine == "local":
        return LocalConverter()
    if engine == "jina":
        return JinaConverter(api_key=api_key, retries=retries)
    if engine == "openai":
        return OpenAIConverter(
            base_url=base_url,
            api_key=api_key or "ollama",
            model=model,
            retries=retries,
            client=None,
        )
    raise ValueError(f"Unknown engine: {engine!r} (expected local|jina|openai)")
