import json

import httpx
import pytest
import respx

from docs_to_md.engines import JinaConverter, LocalConverter, OpenAIConverter, Page, make_converter

from .conftest import PAGE_HTML_TEMPLATE

JINA_API = "https://r.jina.ai"


async def test_local_converter(page_html):
    page = Page("intro", "https://x.test/intro.html", html=page_html)
    async with httpx.AsyncClient() as client:
        md = await LocalConverter().convert(client, page)
    assert "# A Page" in md
    assert "**content**" in md
    assert "nav junk" not in md


async def test_jina_converter_posts_url_with_auth():
    page = Page("intro", "https://x.test/intro.html")
    with respx.mock:
        route = respx.post(JINA_API).respond(200, text="# from jina")
        async with httpx.AsyncClient() as client:
            md = await JinaConverter(api_key="secret").convert(client, page)
    assert md == "# from jina"
    request = route.calls[0].request
    assert request.headers["Authorization"] == "Bearer secret"
    assert json.loads(request.content) == {"url": "https://x.test/intro.html"}


async def test_jina_converter_surfaces_errors():
    page = Page("intro", "https://x.test/intro.html")
    with respx.mock:
        respx.post(JINA_API).respond(403, text="nope")
        async with httpx.AsyncClient() as client:
            try:
                await JinaConverter(retries=0).convert(client, page)
            except httpx.HTTPStatusError as exc:
                assert exc.response.status_code == 403
            else:
                raise AssertionError("expected HTTPStatusError")


async def test_openai_converter():
    # openai 3.x talks HTTP through httpx2, which respx cannot intercept;
    # use httpx2's MockTransport with an injected client instead.
    import httpx2
    import openai

    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.url.path == "/v1/chat/completions"
        return httpx2.Response(
            200,
            json={"choices": [{"message": {"content": "# converted"}}]},
        )

    ai = openai.AsyncOpenAI(
        base_url="http://localhost:11434/v1",
        api_key="x",
        http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler)),
    )
    page = Page("intro", "https://x.test/intro.html", html=PAGE_HTML_TEMPLATE.format(title="T"))
    async with httpx.AsyncClient() as client:
        md = await OpenAIConverter(client=ai).convert(client, page)
    assert md == "# converted"


def test_make_converter_factory():
    assert make_converter("local").name == "local"
    assert make_converter("jina").name == "jina"
    assert make_converter("openai", model="m").model == "m"
    with pytest.raises(ValueError, match="Unknown engine"):
        make_converter("bogus")
