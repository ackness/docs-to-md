import httpx
import pytest
import respx

from docs_to_md.utils import (
    discover_sub_urls,
    extract_project_name_from_url,
    fetch_text,
    normalize_index_url,
    preprocess_html,
)

from .conftest import INDEX_HTML, INDEX_URL, PAGE_HTML_TEMPLATE


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://example.com/index.html", "https://example.com/"),
        ("https://x.readthedocs.io/en/latest/", "https://x.readthedocs.io/en/latest/"),
        ("https://x.readthedocs.io/en/latest", "https://x.readthedocs.io/en/latest/"),
        ("https://x.readthedocs.io/en/latest/?a=1#b", "https://x.readthedocs.io/en/latest/"),
    ],
)
def test_normalize_index_url(url, expected):
    assert normalize_index_url(url) == expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://example-sphinx-basic.readthedocs.io/en/latest/", "example-sphinx-basic"),
        ("https://hftbacktest.readthedocs.io/en/py-v2.1.0/", "hftbacktest"),
        ("https://docs.python.org/3/", "3"),
        ("https://numpy.org/", "numpy"),
    ],
)
def test_extract_project_name_from_url(url, expected):
    assert extract_project_name_from_url(url) == expected


def test_discover_sub_urls():
    pages = discover_sub_urls(INDEX_URL, INDEX_HTML)
    assert pages == {
        "intro": "https://example.readthedocs.io/en/latest/intro.html",
        "guide_usage": "https://example.readthedocs.io/en/latest/guide/usage.html",
        "index": INDEX_URL,
    }


def test_preprocess_html_keeps_only_article_body():
    cleaned = preprocess_html(PAGE_HTML_TEMPLATE.format(title="A Page"))
    assert "A Page" in cleaned
    assert "print" in cleaned
    assert "nav junk" not in cleaned
    assert "var x" not in cleaned


def test_preprocess_html_without_article_body_falls_back():
    cleaned = preprocess_html("<html><body><p>plain</p></body></html>")
    assert "plain" in cleaned


async def test_fetch_text_retries_on_429():
    with respx.mock:
        route = respx.get("https://example.com/").mock(
            side_effect=[
                httpx.Response(429, headers={"Retry-After": "0"}),
                httpx.Response(200, text="ok"),
            ]
        )
        async with httpx.AsyncClient() as client:
            assert await fetch_text(client, "https://example.com/") == "ok"
        assert route.call_count == 2


async def test_fetch_text_raises_after_exhausting_retries():
    with respx.mock:
        respx.get("https://example.com/").respond(500)
        async with httpx.AsyncClient() as client:
            with pytest.raises(httpx.HTTPStatusError):
                await fetch_text(client, "https://example.com/", retries=1)
