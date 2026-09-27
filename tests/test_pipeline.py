import respx

from docs_to_md.engines import JinaConverter, LocalConverter
from docs_to_md.pipeline import convert_readthedocs

from .conftest import INDEX_HTML, INDEX_URL, PAGE_HTML_TEMPLATE

INTRO_URL = "https://example.readthedocs.io/en/latest/intro.html"
USAGE_URL = "https://example.readthedocs.io/en/latest/guide/usage.html"


def mock_docs_site(router, fail_intro=False):
    routes = {"index": router.get(INDEX_URL).respond(200, text=INDEX_HTML)}
    if fail_intro:
        routes["intro"] = router.get(INTRO_URL).respond(500)
    else:
        routes["intro"] = router.get(INTRO_URL).respond(
            200,
            text=PAGE_HTML_TEMPLATE.format(title="Intro"),
        )
    routes["usage"] = router.get(USAGE_URL).respond(
        200,
        text=PAGE_HTML_TEMPLATE.format(title="Usage"),
    )
    return routes


async def test_convert_readthedocs_local(tmp_path):
    with respx.mock as router:
        mock_docs_site(router)
        result = await convert_readthedocs(
            INDEX_URL,
            converter=LocalConverter(),
            output_dir=tmp_path,
        )

    assert result.project_name == "example"
    assert len(result.pages) == 3
    assert result.failed == []

    out = tmp_path / "example"
    assert (out / "index.md").exists()
    assert (out / "intro.md").exists()
    assert (out / "guide_usage.md").exists()
    assert "# Intro" in (out / "intro.md").read_text()


async def test_convert_readthedocs_save_html(tmp_path):
    with respx.mock as router:
        mock_docs_site(router)
        result = await convert_readthedocs(
            INDEX_URL,
            converter=LocalConverter(),
            output_dir=tmp_path,
            save_html=True,
        )
    assert (tmp_path / "example" / "html" / "intro.html").exists()
    assert result.failed == []


async def test_convert_readthedocs_jina_does_not_fetch_pages(tmp_path):
    with respx.mock(assert_all_called=False) as router:
        routes = mock_docs_site(router)
        jina = router.post("https://r.jina.ai").respond(200, text="# jina md")
        result = await convert_readthedocs(
            INDEX_URL,
            converter=JinaConverter(api_key="k"),
            output_dir=tmp_path,
        )

    assert jina.call_count == 3  # index + intro + guide/usage
    # sub-pages are converted by jina itself, so no GETs for them
    assert routes["intro"].call_count == 0
    assert routes["usage"].call_count == 0
    assert result.failed == []
    assert (tmp_path / "example" / "intro.md").read_text() == "# jina md"


async def test_convert_readthedocs_collects_page_failures(tmp_path):
    with respx.mock as router:
        mock_docs_site(router, fail_intro=True)
        result = await convert_readthedocs(
            INDEX_URL,
            converter=LocalConverter(),
            output_dir=tmp_path,
            retries=0,
        )

    assert len(result.failed) == 1
    assert result.failed[0].name == "intro"
    assert len(result.succeeded) == 2


async def test_convert_readthedocs_progress_callback(tmp_path):
    calls = []
    with respx.mock as router:
        mock_docs_site(router)
        await convert_readthedocs(
            INDEX_URL,
            converter=LocalConverter(),
            output_dir=tmp_path,
            on_progress=lambda done, total: calls.append((done, total)),
        )
    assert calls[-1] == (3, 3)
