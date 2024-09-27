import pytest
from docs_to_md.utils import extract_project_name_from_url
from docs_to_md.utils import fetch
from docs_to_md.utils import remove_end_html


@pytest.mark.parametrize(
    "url, expected",
    [
        (
            "https://example-sphinx-basic.readthedocs.io/en/latest/",
            "example-sphinx-basic",
        ),
        (
            "https://hftbacktest.readthedocs.io/en/py-v2.1.0/",
            "hftbacktest",
        ),
    ],
)
def test_extract_project_name_from_url(url, expected):
    assert extract_project_name_from_url(url) == expected


@pytest.mark.asyncio
async def test_fetch():
    html = await fetch("https://example.com")
    assert html is not None


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://example.com/index.html", "https://example.com"),
        (
            "https://example-sphinx-basic.readthedocs.io/en/latest/index.html",
            "https://example-sphinx-basic.readthedocs.io/en/latest",
        ),
    ],
)
def test_remove_end_html(url, expected):
    assert remove_end_html(url) == expected
